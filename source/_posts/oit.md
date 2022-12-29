---
title: 【UE5】浅析UE5.1OIT半透明排序算法
date: 2022-11-29 19:24
count: true
tags: Engine
category: 文章
dplayer: true
cover: https://w.wallhaven.cc/full/z8/wallhaven-z8lmpo.jpg
---

# 前言

UE在5.1更新了OIT算法,其算法原理很简单，把半透明重写写入深度进行排序和颜色混合。这里主要记录一些细节和官方的做法，同时也水一篇文章

# 原理

首先UE有两种OIT排序，一个是EOITSortingType::SortedTriangles三角面排序，另一个是EOITSortingType::SortedPixels

# SortedTriangles

其中三角面排序，可以直接在component里面打开
![](https://pic2.zhimg.com/80/v2-7e23f29ca4f61006efa555621d970425_720w.webp)
只能解决半透明物体自身的排序而不能解决多个物体之间的半透明排序。图中有些重叠的面是排序错误的，而且还会产生面之间的闪烁。因为现在还是实验性功能，所以未来肯定会得到解决。

这功能会在DeferredShadingRenderer里面RenderTranslucency前面调用OIT::AddSortTrianglesPass去排序。

做法是先把要排序的物体三角面的中心点在shader里转化为屏幕坐标，然后用屏幕坐标的z，就是深度，转换到mesh bound里面深度
```c++ ""
const float fSliceIndex = saturate((ViewP.z - ViewBoundMinZ) / (ViewBoundMaxZ - ViewBoundMinZ));
```
得到index限制0到31,要是nVidia设备就是64，因为compute shader每个group的buffer设置为32个线程。然后把求得的深度放入shared memory对应的index中写入，进行原子操作，要是里面已经有写入了，就偏移一位,最后按照primitive id写入buffer，之后在下一个pass把排序好的index获取他的三个顶点写出到输出buffer上。

之后会把之前的indexbuffer替換为这个buffer。具体可以查看OIT.cpp里面的AddOITSortTriangleIndexPass函数

# SortedPixels

而用像素排序则可以解决各个透明排序的问题,用的是Multi-Layer Alpha Blending(MLAB)技术，但跟MLAB技术有点区别
https://zhuanlan.zhihu.com/p/368065919
首先会开四张贴图，颜色、透射比、深度、当前需要的排序次数，这里有个小优化就是排序最大的次数是你当前像素的min（overdraw，自己设定最大排序次数）
![](https://pic2.zhimg.com/80/v2-0f9f7ff716907ada51d7e42871e3b469_720w.webp)
分辨率是你最大采样个数开方向下取整X窗口分辨率，就是说会把多张pass合成一张大的，是R32格式的，最后会颜色R11G11B10F压缩进这帖图了。

在渲染半透明物体时候会填充这些pass，按深度近向远简单填充和插入这些pass中,然后接下来会调用OIT::AddOITComposePass这函数去混合，而混合的时候会进行一次Bubble sort，最后把所有颜色*折射比从最近到远加起来。

顺便说一下，现版本5.2要是场景没有半透明物体，依然会新开pass和清理pass，这点消耗就有点没必要了
![](https://pic2.zhimg.com/80/v2-b4c90d895217064e6c5a3c693cfd2129_720w.webp)