import ee

# from model.RefinedLee import bands_transform

def VV_VH_diff(img):
    
    vv_band = img.select('VV')
    vh_band = img.select('VH')

    dem = ee.Image('USGS/SRTMGL1_003');
    aspect_band = ee.Terrain.aspect(dem).clip(img.geometry())

    # 检查轨道属性值并执行操作
    orbit_pass = img.get('orbitProperties_pass')
# *******************************************************************************
    # 在服务器端定义条件
    aspectCondition_shadow = ee.Algorithms.If(orbit_pass == 'ASCENDING', \
                                              aspect_band.gt(0).And(aspect_band.lt(180)),\
                                              aspect_band.gte(180).And(aspect_band.lt(360)))
    
    aspectCondition_light = ee.Algorithms.If(orbit_pass =='ASCENDING', \
                                             aspect_band.gte(180).And(aspect_band.lt(360)),\
                                             aspect_band.gt(0).And(aspect_band.lt(180)))
    
    Condition_shadow = ee.Image(aspectCondition_shadow)
    Condition_light = ee.Image(aspectCondition_light)
 
    shadow_vv = vv_band.multiply(Condition_shadow)
    shadow_vh = vh_band.multiply(Condition_shadow)

    light_vv = vv_band.multiply(Condition_light)
    light_vh = vh_band.multiply(Condition_light)
    
    # 计算均值
    vv_mean_shadow = shadow_vv.reduceRegion(reducer=ee.Reducer.mean(), geometry=img.geometry(), scale=90).get('VV')
    vh_mean_shadow = shadow_vh.reduceRegion(reducer=ee.Reducer.mean(), geometry=img.geometry(), scale=90).get('VH')

    vv_mean_light = light_vv.reduceRegion(reducer=ee.Reducer.mean(), geometry=img.geometry(), scale=90).get('VV')
    vh_mean_light = light_vh.reduceRegion(reducer=ee.Reducer.mean(), geometry=img.geometry(), scale=90).get('VH')

    # 转换为图像对象
    vv_mean_shadow_img = ee.Image.constant(vv_mean_shadow)
    vv_mean_light_img = ee.Image.constant(vv_mean_light)
    vh_mean_shadow_img = ee.Image.constant(vh_mean_shadow)
    vh_mean_light_img = ee.Image.constant(vh_mean_light)

    # 计算差值   
    vv_mean_diff = vv_mean_shadow_img.subtract(vv_mean_light_img).abs().clip(img.geometry())
    vh_mean_diff = vh_mean_shadow_img.subtract(vh_mean_light_img).abs().clip(img.geometry())
    
    vv_plus = vv_band.add(Condition_light.multiply(vv_mean_diff))
    vh_plus = vh_band.add(Condition_light.multiply(vh_mean_diff))

    VV_VH_plus = vv_plus
    VV_VH_plus = VV_VH_plus.addBands(vh_plus.select('VH'))
    VV_VH_plus = VV_VH_plus.set('system:time_start', img.get('system:time_start')).set('system:index', img.get('system:index'))

    return VV_VH_plus #可以正常输出 VV_VH_diff_s1
