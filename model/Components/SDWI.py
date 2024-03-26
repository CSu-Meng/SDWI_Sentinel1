import ee
def Resample(image, scale):
    # 指定要降低的分辨率级别
    # 例如，将分辨率降低到原来的 1/4 scale=4

    # 使用 reduceResolution 方法降低图像分辨率
    reduced_image = image.reduceResolution(
        reducer=ee.Reducer.mean(),  # 指定降低分辨率时使用的统计方法，这里使用平均值
    ).reproject(
        crs=image.projection(),  # 保持原始投影
        scale=image.projection().nominalScale().multiply(scale)  # 计算新的分辨率
    )
    return reduced_image

def SDWI(img):
    vv_band = img.select('VV')
    vh_band = img.select('VH')
    
    x = vv_band.multiply(vh_band).multiply(10)
    y = (x).log()
    SDWI = y.subtract(8)
    SDWI = Resample(SDWI,1).gt(0)    

    result = SDWI.select('VV').rename('SDWI')
    # year_month = img.date().format('YYYY_MM')
    result = result.set('system:time_start', img.get('system:time_start'))

       
    # image = image
    return ee.Image(result.uint8())