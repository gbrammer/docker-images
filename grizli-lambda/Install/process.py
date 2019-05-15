"""
Helper function for running Grizli redshift fits in AWS lambda

event = {'s3_object_path' : 'Pipeline/j001452+091221/Extractions/j001452+091221_00277.beams.fits'}

Optional event keys:

    'verbose' : verbose output
    
    'skip_started' : Look for a start.log file and abort if found
    
    'check_wcs' : check for WCS files, needed for ACS fits
    
    'quasar_fit' : run fit with quasar templates
    
    'use_psf' : Use point source models (for quasar fits)
    
    'output_path' : optional output path in the aws-grivam bucket
    
    'zr' : [zmin, zmax] Redshift fitting range
    
"""

import os
import glob
import time

import numpy as np

import grizli
from grizli import fitting, utils
utils.set_warnings()

import boto3

def run_grizli_fit(event):
    
    #event = {'s3_object_path':'Pipeline/j001452+091221/Extractions/j001452+091221_00277.beams.fits'}
    
    ###
    ### Parse event booleans
    ### 
    event_bools = {}
    for k in ['verbose', 'check_wcs', 'quasar_fit', 'use_psf', 'skip_started']:
        if k in event:
            event_bools[k] = event[k].lower() in ["true", True]
        else:
            event_bools[k] = False
    
    print('Grizli version: ', grizli.__version__)
    
    ## Output path
    if 'output_path' in event:
        output_path = event['output_path']
    else:
        output_path = None
    
    if 'bucket' in event:
        event_bools['bucket'] = event['bucket']
    else:
        event_bools['bucket'] = 'aws-grivam'
                        
    os.chdir('/tmp/')
    os.system('cp {0}/matplotlibrc .'.format(grizli.GRIZLI_PATH))
    
    s3 = boto3.resource('s3')
    s3_client = boto3.client('s3')
    bkt = s3.Bucket(event_bools['bucket'])

    beams_file = os.path.basename(event['s3_object_path'])
    root = beams_file.split('_')[0]
    id = int(beams_file.split('_')[1].split('.')[0])
     
    # Initial log
    start_log = '{0}_{1:05d}.start.log'.format(root, id)
    full_start = 'Pipeline/{0}/Extractions/{1}'.format(root, start_log)
    
    if event_bools['skip_started']:
        res = [r.key for r in bkt.objects.filter(Prefix=full_start)]
        if res:
            print('Already started ({0}), aborting.'.format(start_log))
    
    fp = open(start_log,'w')
    fp.write(time.ctime()+'\n')
    fp.close()
    bkt.upload_file(start_log, full_start)
    
    if event_bools['check_wcs']:
        # WCS files for ACS
        files = [obj.key for obj in bkt.objects.filter(Prefix='Pipeline/{0}/Extractions/j'.format(root))]
        for file in files:
            if 'wcs.fits' in file:
                bkt.download_file(file, os.path.basename(file),
                                  ExtraArgs={"RequestPayer": "requester"})
 
    # Download files for the fit
    bkt.download_file(event['s3_object_path'], './{0}'.format(beams_file), ExtraArgs={"RequestPayer": "requester"})

    bkt.download_file('Pipeline/{0}/Extractions/fit_args.npy'.format(root), './fit_args.npy', ExtraArgs={"RequestPayer": "requester"})
    
    # Is zr in the event dict?
    if 'zr' in event:
        zr = list(np.cast[float](event['zr']))
    else:
        try:
            zr = np.load('fit_args.npy')[0]['zr']
        except:
            zr = np.load('fit_args.npy', allow_pickle=True)[0]['zr']
            
    ###   
    ### Run the fit
    
    if event_bools['quasar_fit']:
        
        # Quasar templates
        t0, t1 = utils.load_quasar_templates(uv_line_complex=False,
                                            broad_fwhm=2800, narrow_fwhm=1000,
                                            fixed_narrow_lines=True)
        
        fitting.run_all_parallel(id, t0=t0, t1=t1, fit_only_beams=True,
                                 fit_beams=False,  zr=zr,
                                 use_psf=event_bools['use_psf'],
                                 verbose=event_bools['verbose'])
        
        if output_path is None:
            output_path = 'Pipeline/QuasarFit'.format(root)
        
    else:
        
        # Normal galaxy redshift fit
        fitting.run_all_parallel(id, zr=zr, fit_only_beams=True,
                                 fit_beams=False,  
                                 verbose=event_bools['verbose'])
        
        if output_path is None:
            output_path = 'Pipeline/{0}/Extractions'.format(root)
        
    # Output files
    files = glob.glob('{0}_{1:05d}*'.format(root, id))
    for file in files:
        if 'beams.fits' not in file:
            aws_file = '{0}/{1}'.format(output_path, file)
            print(aws_file)
            bkt.upload_file(file, aws_file, ExtraArgs={'ACL': 'public-read'})
    
    # Remove start log now that done
    res = bkt.delete_objects(Delete={'Objects':[{'Key':full_start}]})
    
TESTER = 'Pipeline/j001452+091221/Extractions/j001452+091221_00277.beams.fits'
def run_test(s3_object_path=TESTER):
    event = {'s3_object_path': s3_object_path, 'verbose':'True'}
    run_grizli_fit(event)
    
def handler(event, context):
    print(event) #['s3_object_path'], event['verbose'])
    run_grizli_fit(event)

def show_version(event, context):
    import grizli
    import eazy
    
    print('Event: ', event)
    
    print('grizli version: ', grizli.__version__)
    print('eazy version: ', eazy.__version__)
    
    import matplotlib
    print('matplotlibrc: ', matplotlib.matplotlib_fname())
    
if __name__ == "__main__":
    handler('', '')
