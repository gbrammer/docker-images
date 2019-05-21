#!/bin/env python

def group_by_filter():
    """
    aws s3 sync --exclude "*" --include "cosmos_visits*" s3://grizli-preprocess/CosmosMosaic/ ./ 
    
    """
    from grizli import prep, utils
    import numpy as np
    
    master='cosmos'
    master='grizli-jan2019'
    
    tab = utils.read_catalog('{0}_visits.fits'.format(master))
    all_visits = np.load('{0}_visits.npy'.format(master))[0]
    
    # By filter
    
    # Exclude DASH
    dash = utils.column_string_operation(tab['product'], 'icxe', 'startswith')
    
    # Don't exclude DASH
    dash = utils.column_string_operation(tab['product'], 'xxxx', 'startswith')
    
    groups = {}
    fpstr = {}
    
    for filt in np.unique(tab['filter']):
        mat = (tab['filter'] == filt) & (~dash)
        groups[filt] = {'filter':filt, 'files':[], 'awspath':[], 'footprints':[]}
        fpstr[filt] = 'fk5\n'
        
        for ix in np.where(mat)[0]:
            fp = all_visits[ix]['footprint']
            if hasattr(fp, '__len__'):
                fps = fp
            else:
                fps = [fp]
            for fp in fps: 
                xy = fp.boundary.xy
                pstr = 'polygon('+','.join(['{0:.6f}'.format(i) for i in np.array([xy[0].tolist(), xy[1].tolist()]).T.flatten()])+') # text={{{0}}}\n'.format(all_visits[ix]['product'])
            
                fpstr[filt] += pstr
            
            for k in ['files', 'awspath','footprints']:
                groups[filt][k].extend(all_visits[ix][k])
        
        fp = open('{0}-pointings-{1}.reg'.format(master, filt),'w')
        fp.write(fpstr[filt])
        fp.close()
    
        print('{0} {1:>3d} {2:>4d}'.format(filt, mat.sum(), len(groups[filt]['files'])))
    
    np.save('{0}_filter_groups.npy'.format(master), [groups])
    
RGB_PARAMS = {'xsize':4, 'rgb_min':-0.01, 'verbose':True, 'output_dpi': None, 'add_labels':False, 'output_format':'png', 'show_ir':False, 'scl':2, 'suffix':'.rgb', 'mask_empty':False}

#xsize=4, output_dpi=None, HOME_PATH=None, show_ir=False, pl=1, pf=1, scl=1, rgb_scl=[1, 1, 1], ds9=None, force_ir=False, filters=all_filters, add_labels=False, output_format='png', rgb_min=-0.01, xyslice=None, pure_sort=False, verbose=True, force_rgb=None, suffix='.rgb', scale_ab=scale_ab)

def drizzle_images(label='macs0647-jd1', ra=101.9822125, dec=70.24326667, pixscale=0.06, size=10, wcs=None, pixfrac=0.8, kernel='square', theta=0, half_optical_pixscale=False, filters=['f160w','f814w', 'f140w','f125w','f105w','f110w','f098m','f850lp', 'f775w', 'f606w','f475w','f555w','f600lp', 'f390w', 'f350lp'], remove=True, rgb_params=RGB_PARAMS, master='grizli-jan2019', aws_bucket='s3://grizli/CutoutProducts/', scale_ab=21, thumb_height=2.0, sync_fits=True, subtract_median=True, include_saturated=True, include_ir_psf=False):
    """
    label='cp561356'; ra=150.208875; dec=1.850241667; size=40; filters=['f160w','f814w', 'f140w','f125w','f105w','f606w','f475w']
    
    
    """
    import glob
    import copy
    import os

    import numpy as np
    
    import astropy.io.fits as pyfits
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    from drizzlepac.adrizzle import do_driz
    
    import boto3
    
    from grizli import prep, utils
    from grizli.pipeline import auto_script
    
    if isinstance(ra, str):
        coo = SkyCoord('{0} {1}'.format(ra, dec), unit=(u.hour, u.deg))
        ra, dec = coo.ra.value, coo.dec.value
    
    if label is None:
        try:
            import mastquery.utils
            label = mastquery.utils.radec_to_targname(ra=ra, dec=dec, round_arcsec=(1/15, 1), targstr='j{rah}{ram}{ras}{sign}{ded}{dem}{des}')
        except:
            label = 'grizli-cutout'
            
    #master = 'cosmos'
    #master = 'grizli-jan2019'
    
    if master == 'grizli-jan2019':
        parent = 's3://grizli/MosaicTools/'

        s3 = boto3.resource('s3')
        s3_client = boto3.client('s3')
        bkt = s3.Bucket('grizli')
    
    elif master == 'cosmos':
        parent = 's3://grizli-preprocess/CosmosMosaic/'

        s3 = boto3.resource('s3')
        s3_client = boto3.client('s3')
        bkt = s3.Bucket('grizli-preprocess')
    
    else:
        # Run on local files, e.g., "Prep" directory
        parent = None
        remove = False
        
    for ext in ['_visits.fits', '_visits.npy', '_filter_groups.npy'][-1:]:

        if (not os.path.exists('{0}{1}'.format(master, ext))) & (parent is not None):
            
            s3_path = parent.split('/')[-2]
            s3_file = '{0}{1}'.format(master, ext)
            print('{0}{1}'.format(parent, s3_file))
            bkt.download_file(s3_path+'/'+s3_file, s3_file,
                              ExtraArgs={"RequestPayer": "requester"})
            
            #os.system('aws s3 cp {0}{1}{2} ./'.format(parent, master, ext))
            
    #tab = utils.read_catalog('{0}_visits.fits'.format(master))
    #all_visits = np.load('{0}_visits.npy'.format(master))[0]
    if parent is not None:
        groups = np.load('{0}_filter_groups.npy'.format(master), allow_pickle=True)[0]
    else:
        # Reformat local visits.npy into a groups file
        groups_files = glob.glob('*filter_groups.npy')
        
        if len(groups_files) == 0:
            visit_file = glob.glob('*visits.npy')[0]
            visits, groups, info = np.load(visit_file)
            visit_root = visit_file.split('_visits')[0]
            
            visit_filters = np.array([v['product'].split('-')[-1] for v in visits])
            groups = {}
            for filt in np.unique(visit_filters):
                groups[filt] = {}
                groups[filt]['filter'] = filt
                groups[filt]['files'] = []
                groups[filt]['footprints'] = []
                groups[filt]['awspath'] = None
                
                ix = np.where(visit_filters == filt)[0]
                for i in ix:
                    groups[filt]['files'].extend(visits[i]['files'])
                    groups[filt]['footprints'].extend(visits[i]['footprints'])
                
            np.save('{0}_filter_groups.npy'.format(visit_root), [groups])
                
        else:
            groups = np.load(groups_files[0])[0]
        
    #filters = ['f160w','f814w', 'f110w', 'f098m', 'f140w','f125w','f105w','f606w', 'f475w']
    
    has_filts = []
    
    for filt in filters:
        if filt not in groups:
            continue
        
        visits = [copy.deepcopy(groups[filt])]
        #visits[0]['reference'] = 'CarlosGG/ak03_j1000p0228/Prep/ak03_j1000p0228-f160w_drz_sci.fits'
        
        
        visits[0]['product'] = label+'-'+filt

        if wcs is None:
            hdu = utils.make_wcsheader(ra=ra, dec=dec, size=size, pixscale=pixscale, get_hdu=True, theta=theta)

            h = hdu.header
        else:
            h = utils.to_header(wcs)
            
        if (filt[:2] in ['f0', 'f1', 'g1']) | (not half_optical_pixscale):
            #data = hdu.data  
            pass
        else:
            for k in ['NAXIS1','NAXIS2','CRPIX1','CRPIX2']:
                h[k] *= 2

            h['CRPIX1'] -= 0.5
            h['CRPIX2'] -= 0.5

            for k in ['CD1_1', 'CD1_2', 'CD2_1', 'CD2_2']:
                h[k] /= 2

            #data = np.zeros((h['NAXIS2'], h['NAXIS1']), dtype=np.int16)
                        
        #pyfits.PrimaryHDU(header=h, data=data).writeto('ref.fits', overwrite=True, output_verify='fix')
        #visits[0]['reference'] = 'ref.fits'
        
        print('\n\n###\nMake filter: {0}'.format(filt))
        
        
        if (filt.upper() in ['F105W','F125W','F140W','F160W']) & include_ir_psf:
            clean_i = False
        else:
            clean_i = remove
            
        status = utils.drizzle_from_visit(visits[0], h, pixfrac=pixfrac, kernel=kernel, clean=clean_i, include_saturated=include_saturated)
        
        if status is not None:
            sci, wht, outh = status
            
            if subtract_median:
                med = np.median(sci[sci != 0])
                print('\n\nMedian {0} = {1:.3f}\n\n'.format(filt, med))
                sci -= med
                outh['IMGMED'] = (med, 'Median subtracted from the image')
            else:
                med = 0.
                outh['IMGMED'] = (med, 'Median subtracted from the image')
                
            pyfits.writeto('{0}-{1}_drz_sci.fits'.format(label, filt), 
                           data=sci, header=outh, overwrite=True, 
                           output_verify='fix')
            
            pyfits.writeto('{0}-{1}_drz_wht.fits'.format(label, filt), 
                           data=wht, header=outh, overwrite=True, 
                           output_verify='fix')
            
            has_filts.append(filt)
            
            if (filt.upper() in ['F105W','F125W','F140W','F160W']) & include_ir_psf:
                from grizli.galfit.psf import DrizzlePSF
                
                hdu = pyfits.open('{0}-{1}_drz_sci.fits'.format(label, filt),
                                  mode='update') 
                
                flt_files = [] #visits[0]['files']
                for i in range(1, 10000):
                    key = 'FLT{0:05d}'.format(i)
                    if key not in hdu[0].header:
                        break
                    
                    flt_files.append(hdu[0].header[key])
                        
                dp = DrizzlePSF(flt_files=flt_files, driz_hdu=hdu[0])
                
                psf = dp.get_psf(ra=dp.driz_wcs.wcs.crval[0],
                                 dec=dp.driz_wcs.wcs.crval[1], 
                                 filter=filt.upper(), 
                                 pixfrac=dp.driz_header['PIXFRAC'], 
                                 kernel=dp.driz_header['KERNEL'], 
                                 wcs_slice=dp.driz_wcs, get_extended=True, 
                                 verbose=False, get_weight=False)

                psf[1].header['EXTNAME'] = 'PSF'
                #psf[1].header['EXTVER'] = filt
                hdu.append(psf[1])
                hdu.flush()
                
                #psf.writeto('{0}-{1}_drz_sci.fits'.format(label, filt), 
                #            overwrite=True, output_verify='fix')
                
        #status = prep.drizzle_overlaps(visits, parse_visits=False, check_overlaps=True, pixfrac=pixfrac, skysub=False, final_wcs=True, final_wht_type='IVM', static=True, max_files=260, fix_wcs_system=True)
        # 
        # if len(glob.glob('{0}-{1}*sci.fits'.format(label, filt))):
        #     has_filts.append(filt)
            
        if remove:
            os.system('rm *_fl*fits')
         
    if len(has_filts) == 0:
        return []
    
    if rgb_params:
        #auto_script.field_rgb(root=label, HOME_PATH=None, filters=has_filts, **rgb_params)
        
        show_all_thumbnails(label=label, thumb_height=thumb_height, scale_ab=scale_ab, close=True, rgb_params=rgb_params)
        
    if aws_bucket:   
        #aws_bucket = 's3://grizli-cosmos/CutoutProducts/'
        #aws_bucket = 's3://grizli/CutoutProducts/'
        
        s3 = boto3.resource('s3')
        s3_client = boto3.client('s3')
        bkt = s3.Bucket(aws_bucket.split("/")[2])
        aws_path = '/'.join(aws_bucket.split("/")[3:])
        
        if sync_fits:
            files = glob.glob('{0}*'.format(label))
        else:
            files = glob.glob('{0}*png'.format(label))
            
        for file in files: 
            print('{0} -> {1}'.format(file, aws_bucket))
            bkt.upload_file(file, '{0}/{1}'.format(aws_path, file).replace('//','/'), ExtraArgs={'ACL': 'public-read'})
            
        #os.system('aws s3 sync --exclude "*" --include "{0}*" ./ {1} --acl public-read'.format(label, aws_bucket))
    
        #os.system("""echo "<pre>" > index.html; aws s3 ls AWSBUCKETX --human-readable | sort -k 1 -k 2 | grep -v index | awk '{printf("%s %s",$1, $2); printf(" %6s %s ", $3, $4); print "<a href="$5">"$5"</a>"}'>> index.html; aws s3 cp index.html AWSBUCKETX --acl public-read""".replace('AWSBUCKETX', aws_bucket))
    
    return has_filts

def get_cutout_from_aws(label='macs0647-jd1', ra=101.9822125, dec=70.24326667, master='grizli-jan2019', scale_ab=21, thumb_height=2.0, remove=1, aws_bucket="s3://grizli/DropoutThumbnails/", lambda_func='grizliImagingCutout', force=False, **kwargs):
    """
    Get cutout using AWS lambda
    """    
    import boto3
    import json
    
    #func = 'grizliImagingCutout'
    
    #label = '{0}_{1:05d}'.format(self.cat['root'][ix], self.cat['id'][ix])
    #url = 'https://s3.amazonaws.com/grizli/DropoutThumbnails/{0}.thumb.png'
    
    session = boto3.Session()
    client = session.client('lambda', region_name='us-east-1')
            
    event = {
          'label': label,
          "ra": ra,
          "dec": dec,
          "scale_ab": scale_ab,
          "thumb_height": thumb_height,
          "aws_bucket":aws_bucket,
          "remove":remove,
          "master":master,
        }
    
    for k in kwargs:
        event[k] = kwargs[k]
        
    bucket_split = aws_bucket.strip("s3://").split('/')
    bucket_name = bucket_split[0]
    bucket_path = '/'.join(bucket_split[1:])
    
    s3 = boto3.resource('s3')
    s3_client = boto3.client('s3')
    bkt = s3.Bucket(bucket_name)
    
    files = [obj.key for obj in bkt.objects.filter(Prefix='{0}/{1}.thumb.png'.format(bucket_path, label))]
    
    if (len(files) == 0) | force:
        print('Call lambda: {0}'.format(label))
        response = client.invoke(
            FunctionName=lambda_func,
            InvocationType='Event',
            LogType='Tail',
            Payload=json.dumps(event))
    else:
        response = None
        print('Thumb exists')
        
    return response
    
def handler(event, context):
    import os
    os.chdir('/tmp/')
    os.system('rm *')
    
    print(event) #['s3_object_path'], event['verbose'])
    drizzle_images(**event)

def show_all_thumbnails(label='j022708p4901_00273', filters=['vis','f098m','f105w','f110w','f125w','f140w','f160w'], scale_ab=21, close=True, thumb_height=2., rgb_params=RGB_PARAMS):
    """
    Show individual filter and RGB thumbnails
    """
    import glob

    #from PIL import Image
    
    import numpy as np
    import matplotlib.pyplot as plt
    
    import astropy.io.fits as pyfits
    from astropy.visualization import make_lupton_rgb
    from grizli.pipeline import auto_script
    from grizli import utils
    
    all_files = glob.glob('{0}-f*sci.fits'.format(label))
    all_filters = [f.split('_dr')[0].split('-')[-1] for f in all_files]
    
    ims = {}
    for filter in filters:
        drz_files = glob.glob('{0}-{1}*_dr*sci.fits'.format(label, filter))
        if len(drz_files) > 0:
            im = pyfits.open(drz_files[0])
            ims[filter] = im
    
    rgb_params['scale_ab'] = scale_ab
            
    slx, sly, rgb_filts, fig = auto_script.field_rgb(root=label, HOME_PATH=None, **rgb_params) #xsize=4, output_dpi=None, HOME_PATH=None, show_ir=False, pl=1, pf=1, scl=1, rgb_scl=[1, 1, 1], ds9=None, force_ir=False, filters=all_filters, add_labels=False, output_format='png', rgb_min=-0.01, xyslice=None, pure_sort=False, verbose=True, force_rgb=None, suffix='.rgb', scale_ab=scale_ab)
    if close:
        plt.close()
    
    filter_queries = {}
    filter_queries['vis'] = '{0}-f[3-8]*sci.fits'.format(label)
    filter_queries['y'] = '{0}-f[01][90][85]*sci.fits'.format(label)
    filter_queries['j'] = '{0}-f1[12][05]*sci.fits'.format(label)
    filter_queries['h'] = '{0}-f1[64]0*sci.fits'.format(label)
    
    if 'vis' in filters:
        drz_files = glob.glob('{0}-f[3-8]*sci.fits'.format(label))
        drz_files.sort()
        vis_filters = [f.split('_dr')[0].split('-')[-1] for f in drz_files]
        
        if len(drz_files) > 0:
            drz_files.sort()
            
            for i, file in enumerate(drz_files[::-1]):
                drz = pyfits.open(file)
                wht = pyfits.open(file.replace('_sci','_wht'))
                if i == 0:
                    photflam = drz[0].header['PHOTFLAM']
                
                    num = drz[0].data*wht[0].data
                    den = wht[0].data
                    drz_ref = drz
                    drz_ref[0].header['FILTER{0}'.format(i+1)] = utils.get_hst_filter(drz[0].header)
                    
                else:
                    scl = drz[0].header['PHOTFLAM']/photflam
                    num += drz[0].data*wht[0].data/scl
                    den += wht[0].data/scl**2
                    
                    drz_ref[0].header['FILTER{0}'.format(i+1)] = utils.get_hst_filter(drz[0].header)
                    
            sci = num/den
            sci[den == 0] = 0
            drz_ref[0].data  = sci
            ims['vis'] = drz_ref
            
            pyfits.writeto('{0}-{1}_drz_sci.fits'.format(label, 'vis'), 
                           data=sci, header=drz_ref[0].header, overwrite=True, 
                           output_verify='fix')
            
            pyfits.writeto('{0}-{1}_drz_wht.fits'.format(label, 'vis'), 
                           data=den, header=drz_ref[0].header, overwrite=True, 
                           output_verify='fix')
            
    #rgb = np.array(Image.open('{0}.rgb.png'.format(label)))
    rgb = plt.imread('{0}.rgb.png'.format(label))
    
    NX = (len(filters)+1)
    fig = plt.figure(figsize=[thumb_height*NX, thumb_height])
    ax = fig.add_subplot(1,NX,NX)
    ax.imshow(rgb, origin='upper', interpolation='nearest')
    ax.text(0.05, 0.95, label, ha='left', va='top', transform=ax.transAxes, fontsize=7, color='w', bbox=dict(facecolor='k', edgecolor='None', alpha=0.8))
    ax.text(0.05, 0.05, ' '.join(rgb_filts), ha='left', va='bottom', transform=ax.transAxes, fontsize=6, color='w', bbox=dict(facecolor='k', edgecolor='None', alpha=0.8))
    
    for i, filter in enumerate(filters):
        if filter in ims:
            zp_i = utils.calc_header_zeropoint(ims[filter], ext=0)
            scl = 10**(-0.4*(zp_i-5-scale_ab))
            img = ims[filter][0].data*scl

            image = make_lupton_rgb(img, img, img, stretch=0.1, minimum=-0.01)
            
            ax = fig.add_subplot(1,NX,i+1)
            ax.imshow(255-image, origin='lower', interpolation='nearest')
            
            if filter == 'vis':
                ax.text(0.05, 0.95, '+'.join(vis_filters), ha='left', va='top', transform=ax.transAxes, fontsize=7, bbox=dict(facecolor='w', edgecolor='None', alpha=0.9))
            else:
                ax.text(0.05, 0.95, filter, ha='left', va='top', transform=ax.transAxes, fontsize=7, bbox=dict(facecolor='w', edgecolor='None', alpha=0.9))
    
    for ax in fig.axes:
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_xticks([])
        ax.set_yticks([])
    
    fig.tight_layout(pad=0.1)
    
    fig.savefig('{0}.thumb.png'.format(label))
    if close:
        plt.close()
        
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 5:        
        print('Usage: aws_drizzler.py cp561356 150.208875 1.850241667 40 ')
        print(sys.argv)
        exit()
    
    #print('xxx')    
    drizzle_images(label=sys.argv[1], ra=float(sys.argv[2]), dec=float(sys.argv[3]), size=float(sys.argv[4]))
  
def go():
    """
    grep -v "\#" QGs.txt | awk '{print "./aws_drizzler.py",$1,$2,$3,"60"}' > run.sh
    grep -v "\#" gomez.txt | awk '{print "./aws_drizzler.py",$1,$2,$3,"60"}' >> run.sh
    
    """
    pass