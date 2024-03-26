import ee

def bands_transform(Constant, img):    
    # 选择新的 VV 和 VH 波段
    newVV = Constant.select('VV')
    newVH = Constant.select('VH')
    # 将新的 VV 和 VH 波段添加到图像中，并将它们重命名为 VVnew 和 VHnew
    img = img.addBands(newVV.rename('VVnew')).addBands(newVH.rename('VHnew'))
    # 选择新添加的 VVnew 和 VHnew 波段，并将它们重命名为 VV 和 VH
    result = img.select(['VVnew', 'VHnew']).rename(['VV', 'VH'])
   
    return ee.Image(result)

# 定义从分贝转换的函数
def toNatural(img):
    Constant = ee.Image.constant(10.0).pow(img.divide(10.0))
    result = bands_transform(Constant, img)    
    # result = ee.Image.constant(10.0).pow(img.divide(10.0))
    return ee.Image(result)
    
# 定义转换成分贝的函数
def toDB(img):
    Constant = ee.Image(img).log10().multiply(10.0)
    result = bands_transform(Constant, img) 
    # result = ee.Image(img).log10().multiply(10.0)
    return ee.Image(result)
    
# 定义RefinedLee主函数
def RefinedLee(img):
# 设置3x3内核
  img2 = img
  weights3 = ee.List.repeat(ee.List.repeat(1,3),3)
  kernel3 = ee.Kernel.fixed(3,3, weights3, 1, 1, False)
  mean3 = img2.reduceNeighborhood(ee.Reducer.mean(), kernel3)
  variance3 = img2.reduceNeighborhood(ee.Reducer.variance(), kernel3)
# 使用7x7窗口内的3x3窗口的样本来确定梯度和方向
  sample_weights = ee.List([[0,0,0,0,0,0,0], [0,1,0,1,0,1,0],[0,0,0,0,0,0,0], [0,1,0,1,0,1,0], [0,0,0,0,0,0,0], [0,1,0,1,0,1,0],[0,0,0,0,0,0,0]])
  sample_kernel = ee.Kernel.fixed(7,7, sample_weights, 3,3, False)
# 计算采样窗口的均值和方差，存储为9个波段
  sample_mean = mean3.neighborhoodToBands(sample_kernel); 
  sample_var = variance3.neighborhoodToBands(sample_kernel)
# 确定采样窗口的4个梯度
  gradients = sample_mean.select(1).subtract(sample_mean.select(7)).abs()
  gradients = gradients.addBands(sample_mean.select(6).subtract(sample_mean.select(2)).abs())
  gradients = gradients.addBands(sample_mean.select(3).subtract(sample_mean.select(5)).abs())
  gradients = gradients.addBands(sample_mean.select(0).subtract(sample_mean.select(8)).abs())
# 找到梯度带中的最大梯度
  max_gradient = gradients.reduce(ee.Reducer.max())
# 为最大梯度波段像素创建一个掩码
  gradmask = gradients.eq(max_gradient)
# 重复的渐变带: 每个渐变代表2个方向
  gradmask = gradmask.addBands(gradmask)
# 定义八个方向
  directions = sample_mean.select(1).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(7))).multiply(1)
  directions = directions.addBands(sample_mean.select(6).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(2))).multiply(2))
  directions = directions.addBands(sample_mean.select(3).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(5))).multiply(3))
  directions = directions.addBands(sample_mean.select(0).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(8))).multiply(4))
# 接下来的4个是前面4个中的相反—Not()
  directions = directions.addBands(directions.select(0).Not().multiply(5))
  directions = directions.addBands(directions.select(1).Not().multiply(6))
  directions = directions.addBands(directions.select(2).Not().multiply(7))
  directions = directions.addBands(directions.select(3).Not().multiply(8))
# 掩膜所有不是1-8的值
  directions = directions.updateMask(gradmask)
# 堆栈成一个波段图像(由于屏蔽，每个像素只有一个值(1-8)在它的波段，否则被屏蔽)
  directions = directions.reduce(ee.Reducer.sum()) 
#pal = ['ffffff','ff0000','ffff00', '00ff00', '00ffff', '0000ff', 'ff00ff', '000000']
#Map.addLayer(directions.reduce(ee.Reducer.sum()), {min:1, max:8, palette: pal}, 'Directions', False)
  sample_stats = sample_var.divide(sample_mean.multiply(sample_mean))
# 计算局部噪声方差
  sigmaV = sample_stats.toArray().arraySort().arraySlice(0,0,5).arrayReduce(ee.Reducer.mean(), [0])
# 设置7 * 7内核进行方向统计
  rect_weights = ee.List.repeat(ee.List.repeat(0,7),3).cat(ee.List.repeat(ee.List.repeat(1,7),4))
  diag_weights = ee.List([[1,0,0,0,0,0,0], [1,1,0,0,0,0,0], [1,1,1,0,0,0,0], 
    [1,1,1,1,0,0,0], [1,1,1,1,1,0,0], [1,1,1,1,1,1,0], [1,1,1,1,1,1,1]])
  rect_kernel = ee.Kernel.fixed(7,7, rect_weights, 3, 3, False)
  diag_kernel = ee.Kernel.fixed(7,7, diag_weights, 3, 3, False)
# 使用原始内核创建均值和方差堆栈，用相关方向掩膜。
  dir_mean = img2.reduceNeighborhood(ee.Reducer.mean(), rect_kernel).updateMask(directions.eq(1))
  dir_var = img2.reduceNeighborhood(ee.Reducer.variance(), rect_kernel).updateMask(directions.eq(1))
  dir_mean = dir_mean.addBands(img2.reduceNeighborhood(ee.Reducer.mean(), diag_kernel).updateMask(directions.eq(2)))
  dir_var = dir_var.addBands(img2.reduceNeighborhood(ee.Reducer.variance(), diag_kernel).updateMask(directions.eq(2)))
# 然后加上旋转的内核
  for i in range(1,4):
    dir_mean = dir_mean.addBands(img2.reduceNeighborhood(ee.Reducer.mean(), rect_kernel.rotate(i)).updateMask(directions.eq(2*i+1)))
    dir_var = dir_var.addBands(img2.reduceNeighborhood(ee.Reducer.variance(), rect_kernel.rotate(i)).updateMask(directions.eq(2*i+1)))
    dir_mean = dir_mean.addBands(img2.reduceNeighborhood(ee.Reducer.mean(), diag_kernel.rotate(i)).updateMask(directions.eq(2*i+2)))
    dir_var = dir_var.addBands(img2.reduceNeighborhood(ee.Reducer.variance(), diag_kernel.rotate(i)).updateMask(directions.eq(2*i+2)))
# 堆栈到一个单一的波段图像(由于屏蔽，每个像素只有一个值在它的方向波段，否则被屏蔽)
  dir_mean = dir_mean.reduce(ee.Reducer.sum())
  dir_var = dir_var.reduce(ee.Reducer.sum())
# 最终生成过滤值
  varX = dir_var.subtract(dir_mean.multiply(dir_mean).multiply(sigmaV)).divide(sigmaV.add(1.0)).arrayFlatten([['sum']])
  b = varX.divide(dir_var)
  result = dir_mean.add(b.multiply(img2.subtract(dir_mean)))
  # result = result\
  #   .set('system:time_start', img.get('system:time_start'))\
  #   .set('orbitProperties_pass', img.get('orbitProperties_pass'))
    
  result = bands_transform(result, img)
    
  return ee.Image(result)