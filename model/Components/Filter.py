from model.Components.SDWI import Resample
import ee

def filter_HAND_slop(img):
    HAND = ee.Image("MERIT/Hydro/v1_0_1").select('hnd').clip(img.geometry())
    # 获取"VV_plus"波段的投影和分辨率信息
    projection = img.select("SDWI").projection()
    scale = img.select("SDWI").projection().nominalScale()

	# 将"hnd"波段重投影到相同的投影和分辨率下
    HAND_reprojected = HAND.select("hnd").reproject(
        crs=projection,
        scale=scale
    )

    # SDWI_filterHAND = img.select('SDWI').updateMask(HAND_reprojected.lt(30))
    SDWI_filterHAND = img.select('SDWI').multiply(HAND_reprojected.lt(30))
    SDWI_filterHAND = Resample(SDWI_filterHAND,1).gt(0)

    dem = ee.Image('USGS/SRTMGL1_003');
    slope = ee.Terrain.slope(dem).clip(img.geometry()).select('slope')#.resample('bilinear');  # 选择适当的重采样方法;    
    # collection = collection.addBands(slope.rename('slope'))

    # SDWI_filterHANDslop = SDWI_filterHAND.select('SDWI').updateMask(slope.lt(20))#.gt(0)#.updateMask(HAND_reprojected.lt(30))
    SDWI_filterHANDslop = SDWI_filterHAND.select('SDWI').multiply(slope.lt(20))
    result = SDWI_filterHANDslop#.updateMask(SDWI_filterHANDslop.eq(1))
    result = result.set('system:time_start', img.get('system:time_start')).set('system:index', img.get('system:index'))
    return ee.Image(result.uint8())

def meanFilter(img):
    # sdwi = img.select('SDWI')
    mean_SDWI_plus_HAND = img.focal_mean(radius=1,kernelType='square',units='pixels',iterations=1)    
    mean_SDWI_plus_HAND = Resample(mean_SDWI_plus_HAND,1)  
    mean_SDWI_plus_HAND = mean_SDWI_plus_HAND.set('system:time_start', img.get('system:time_start')).set('system:index', img.get('system:index'))
    return ee.Image(mean_SDWI_plus_HAND.uint8())
    
def medianFilter(img):
    median_SDWI = img.focal_median(radius=1,kernelType='square',units='pixels',iterations=1)
    median_SDWI = Resample(median_SDWI, 1)
    median_SDWI = median_SDWI.set('system:time_start', img.get('system:time_start')).set('system:index', img.get('system:index'))
    return median_SDWI


