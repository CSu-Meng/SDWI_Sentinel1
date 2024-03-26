from model.Components import RefinedLee, VV_VH_diff, SDWI, Filter
import ee

def filterS1(filterBounds, starTime, endTime):
    """
    Filter sentinel-1 images.
    
    Args:
        filterBounds: Boundaries used to filter sentinel-1 images.
        starTime: Start date to filter images.[string]
        endTime: End date to filter images.[string]
    
    Returns:
        ImageCollection
    """
    Original_s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')\
                   .filterBounds(filterBounds)\
                   .filterDate(starTime,endTime)
                   ) 
    return ee.ImageCollection(Original_s1)

def water_area(collection, bandName, waterValue, calculateRange):
    """
    Calculate the area of the water body, the area unit is square kilometers.
    
    Args:
        collection:
        bandName: Band name that represents water.[string]
        waterValue: Value that represents water.
        calculateRange: Calculation range.
    
    Returns:
        ImageCollection
    """
    crs = collection.first().projection().getInfo()['crs']
    scale =30# collection.first().projection().nominalScale().getInfo()
    
    # 定义一个函数来计算波段值为1的像元的总面积
    def calculate_area(image):
        area_stats = image.select(bandName).eq(waterValue).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=image.geometry(),
            scale=scale,
            crs=crs,
            maxPixels=1e13
        )
        area = ee.Number(area_stats.get(bandName)).multiply(ee.Number(scale).multiply(scale)).divide(1e6)  # 将面积转换为万平方千米
        return image.set('area_sqkm', area)

    # 对影像集合中的每一幅影像应用计算面积的函数
    result = collection.map(calculate_area)
    
    return result


# def my_SDWI(filterBounds, starTime, endTime):
def my_SDWI(collection):
    """
    Using SDWI method to identify water areas from sentinel1 images.
    
    Args:
        collection:
    
    Returns:
        ImageCollection
    """
    
# Use improved Lee filter to process original image data set
    RefinedLee_s1 = collection.select(['VV','VH'])\
        .map(RefinedLee.toNatural)\
        .map(RefinedLee.RefinedLee)\
        .map(RefinedLee.toDB)
# Reduce the impact of hillshade
    VV_VH_diff_s1 = RefinedLee_s1.map(VV_VH_diff.VV_VH_diff)
# Identify water bodies using SDWI formula
    SDWI_s1_diff = VV_VH_diff_s1.map(SDWI.SDWI)

# Optimize identification results using slope<20 & hand<30 conditions
    SDWI_HAND_slope_diff = SDWI_s1_diff.map(Filter.filter_HAND_slop)
# Use mean filter to denoise the recognition results
    SDWI_HAND_slope_mean_diff = SDWI_HAND_slope_diff.map(Filter.meanFilter)

    def mask(img):    
        year_month = img.date().format('YYYY_MM')   
        result = img.gt(0.5)
        result = result.set('year_month', year_month)\
                    .set('system:time_start', img.get('system:time_start'))\
                    .set('system:index', img.get('system:index'))
    
        return ee.Image(result)
    
    SDWI_final_result = SDWI_HAND_slope_mean_diff.map(mask)    
    
    return ee.ImageCollection(SDWI_final_result)

def SWO(collection):
    """
    Calculating surface water occurrence (SWO).

    Args:
        collection: Monthly water history.Each image contains the attribute "month" 

    Returns:
        Image
    """
    
    Month = collection.aggregate_array('month').distinct()
    def swo_of_month(month):
        month_collection = collection.filter(ee.Filter.eq('month', ee.String(month)))
        if ee.Number(month_collection.size()).gt(ee.Number(0)):
            WD_month = month_collection.sum()
            VO_month = ee.Image.constant(month_collection.size())
            SWO_month = WD_month.divide(VO_month).select('SDWI').rename('SWO')
            return ee.Image(SWO_month)
        else:
            raise ValueError("No data set for the specified month was retrieved.") 

    ImageList = Month.map(swo_of_month)
    SWO_monthCollection = ee.ImageCollection(ImageList)
    SWO_result = SWO_monthCollection.mean().multiply(ee.Image.constant(100)).int8()
    return SWO_result
