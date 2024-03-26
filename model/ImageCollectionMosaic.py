import ee

   

def setYMD(collection):
    """
    Set the "Year, Month, Day" attribute for the image dataset.
    
    Args:
        collection:  
        
    Returns:
        ImageCollection with property 'year_month_day'.
    """    
    def set_ymd(img):
        ymd = ee.String(img.date().format('YYYY_MM_DD'))
        return img.set('year_month_day', ymd) 

    result = collection.map(set_ymd)
    
    return ee.ImageCollection(result)
# .set('system:index', ee.String('OTSU_').cat(property))\
# .set('system:index', property)# 
def mosaic_collection_by_properties(collection, propertiesName, clipRegion):
    """
    Composites all the images in a collection, using the mask.
    
    Args:
        collection:  
        propertiesName: string--'year_month_day'
        clipRegion: The area for image clipping must be a geometry, a Feature or a FeatureCollection.
    
    Returns:
        ImageCollection
    """
    propertyList = collection.aggregate_array(propertiesName).distinct()
   
    def Mosaic(property):          
        return_collection = collection.filter(ee.Filter.eq(propertiesName, property))         
        orbitPass = return_collection.aggregate_array('orbitProperties_pass').distinct()    

        if orbitPass.length().eq(ee.Number(1)):            
            # timeStart = ee.String(return_collection.aggregate_min('system:time_start'))
            timeStart = return_collection.aggregate_min('system:time_start')
            # date = ee.Image(return_collection.first()).date().format('YYYY_MM_DD')
            mosaic_image = return_collection.mosaic().clip(clipRegion)\
                                        .set('system:time_start', timeStart)\
                                        .set('system:index', ee.String('Mosaic_').cat(property))\
                                        .set('orbitProperties_pass', orbitPass.get(0))\
                                        .set('year_month_day', property)\
                                        .set('year_month', return_collection.first().date().format('YYYY_MM'))
        else:
            raise ValueError("The image collection to be merged has multiple or 0 'orbitProperties_pass' properties")   


        return ee.Image(mosaic_image)
    
    mosaic_collection = propertyList.map(Mosaic)
    
    return ee.ImageCollection(mosaic_collection)
