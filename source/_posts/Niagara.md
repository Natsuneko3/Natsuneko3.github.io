---
title: 【UE4】新手特效向Niagara常见问题解决与小技巧分享（不定期更新）
date: 2022-02-12 12:55
count: true
tags: Niagara
category: 文章
cover: https://pica.zhimg.com/v2-147be5e9a1831e26487605bfee955919_1440w.jpg?source=172ae18b
---

# 前言

现在Niagara虽然正式版虽然已经过了两个版本，由于niagara是设计是在程序与美术之间做取舍而设计出来的，他的本质是个computer shader，所以出现要是美术用的话，入门有点难，不像级联那样入门那么简单，因为他存在属性与绑定这程序上的东西。然后我也看到很多人总是问一些很简单而常见的问题，所以我决定写一遍文章做个收集，方便更多使用新手使用niagara的时候不用四处找资料。

# 问题与技巧收集

## 定义粒子的轴向

![](https://pic4.zhimg.com/80/v2-c4801893074e85bbedb23622e14d3843_720w.webp
)
图中alignment是粒子的朝向，facing mode是面向，更方便点的理解就是
![](https://pic4.zhimg.com/80/v2-4cc06dc7d8404717f5d41c1950d49ddf_720w.webp 
"朝向为（0，1，0）面向为（0，0，1）"
)


这两个属性是可以自定义的，需要在他们的模式改为自定义

![](https://pic2.zhimg.com/80/v2-c8f1597dc0ac60e22059bd4b1064ec31_720w.webp
)

![](https://pic2.zhimg.com/80/v2-44ad7730aac4733f14b269d247491145_720w.webp
"然后在粒子属性拖到emitter上，要是没有这两个属性直接像图中这样创建个"
)

![](https://pic3.zhimg.com/80/v2-5046fe5da9cb248a37842344d3d3a936_720w.webp
"每个粒子渲染器属性都是由粒子属性绑定的，所以都是修改的，所以你创建同名属性也同样对粒子渲染属性起作用"
)


## 模型定义轴向

![](https://pic1.zhimg.com/80/v2-f02d00b6790d41e7fd098fbb4ac97ee0_720w.webp
"当你改为速度朝向时候，会把模型的x轴朝向你速度方向"
)
当你改为速度朝向时候，会把模型的x轴朝向你速度方向
正因如此，我们可以修改这个速度绑定来达到我们的指哪打哪，也许你会问，修改了速度的绑定，那我速度怎么办，其实是这样的，mesh render的速度绑定其实就是为了定义模型速度朝向，然后真正的速度在解算模块时候（solve Force and Velocity）就控制了粒子的位置
![](https://pic4.zhimg.com/80/v2-9cbf662dce47a099c8f02206dafac85b_720w.webp
"首先创建个属性"
)

![](https://pic1.zhimg.com/80/v2-d5cf26b20cf9bf53555033718fde5058_720w.webp
"然后改名字，拖进去，改绑定"
)


那么说完简单的模型朝向，接下来就说稍微深入一点的模型旋转，其实修改模型旋转的还有个属性就是

Mesh Orientation，这是个四元数，那么什么是四元数，四元数怎么旋转一个模型，本文就不讨论，我们只需要知道怎么用他

![](https://pic2.zhimg.com/80/v2-fed1a44e4b14b3918a92d6c56953ca39_720w.webp
"四元数是个非常难的东西，好在ue给我们提供许多转换旋转的函数"
)

find quat between是个非常好用的函数，其中from和to两个值的意思是指你要把模型的那一条轴（from）转到那个方向（to）。这样同样实现了指哪打哪的操作。

## 蓝图修改粒子材质

新建个material interface 然后放入粒子材质绑定就可以
![](https://pic3.zhimg.com/80/v2-0646607ff1ce98e2e077b9ee1ea6bc2a_720w.webp
)

## niagara时间轴消失或者过长
![](https://pic1.zhimg.com/80/v2-a56a61449ea52da05e2c7972a66af270_720w.webp
)
时间轴有个小蓝点报错，为bug，不影响使用，4.27以上版本修复，（ue5EA是4.27以下版本），要是觉得不舒服就把timeline关掉，特效师都是去场景调特效。

## 级联的pivot offset
![](https://pic1.zhimg.com/80/v2-2312796578101a73dc7b83c04d7c1324_720w.webp
)

## 设置niagara的时间膨胀

在特效经常用到子弹时间的效果，因为niagara设计原因，并没有直接像级联那样暴露一个参数来设置时间膨胀，可能暂时吧，这时候需要用到蓝图修改一下模拟tick

![](https://pic4.zhimg.com/80/v2-8d140ffd1b77be04cd94bf9f273086ff_720w.webp
)
其中修改Advance Simulation里的Tick Delta second就可以设置时间膨胀了，他的原理就是你冻结当前渲染流程，进入一个新的渲染流程并且tick 使用你的设置的deltatime，完了后在解冻。听不懂这句话没关系，用就行。
![](https://pic2.zhimg.com/80/v2-dd9d0737a84669d0d09b5200f0152ab1_720w.webp
"你想在特效某一个时间段进入时间膨胀也可以"
)


还有一个方法就是修改emitter里面的deltatime属性，乘一个你自己的数，但这样涉及到缩放或者其他那些你都要自己再弄一个delta去乘一个数，有点麻烦
![](https://pic4.zhimg.com/80/v2-1204f10fc7ec965a0239e346e658fc0f_720w.webp
"仅对速度进行时间膨胀"
)


## 读取某一个粒子的属性
![](https://pic3.zhimg.com/80/v2-c65291d977363c710d42b94f1ee8014e_720w.webp
)
新建一个attribute read input，打read就可以搜到，拉引脚搜你想获得的粒子属性类型，然后在attribute上打属性的名字，注意大小写。attribute reader是读取哪一个发射器，particle index是想读这个发射器的哪一个粒子。execution index是本发射器当前执行的粒子的序号，注意这个index不等同id和uniqueID。index在不同模拟中对应的东西也不同，例如在grid 2d中是当前对应的网格index。

当然也通过id获取另一个发射器粒子的属性，搜get 什么什么by id就行。

![](https://pic4.zhimg.com/80/v2-1204f10fc7ec965a0239e346e658fc0f_720w.webp
"用这个module会报错，填上emitter name就好了，emitter name可以为自身，也就是说可以获得自身其他粒子的属性"
)

## 空格键重新播放niagara
选中niagara窗口按空格键可以重新播放niagara，在场景中选中niagara，按？也可以
![](https://pic1.zhimg.com/80/v2-22996b7f654d5a5aae66b5aa9b1c24dc_720w.webp
"选中窗口会有个小黄条（选中就是点击这个窗口随便一个地方"
)


## 自定义事件
创建一个结构体，然后在里面添加一些自己想发送的变量
![](https://pic2.zhimg.com/80/v2-5e0170140cb8e1cd0103b27ebba67dbd_720w.webp
)
![](https://pic2.zhimg.com/80/v2-958454664785527cd4454b5c50dbc721_720w.webp
)



在项目设置添加上自己的结构体，当然也可以添加一个数据类型，就是上面parameter types设置。
![](https://pic2.zhimg.com/80/v2-6293e73660e682e1a0afec60c5fc8eb1_720w.webpnpm 
"打名字就可以找到自己的结构体"
)
![](https://pic2.zhimg.com/80/v2-5e809e057b1014ede8069164a27b3a91_720w.webp
"condition就是发送开关，关的时候就是不发送"
)
![](https://pic4.zhimg.com/80/v2-6eb4f08e0e85f3d215934a65bee146c3_720w.webp
"把module添加到事件里，然后其他emitter就可以接收到"
)


接收也要自己写module并放到事件中，不写的话数据不会有任何变化。

## 4.27 module里的 If 换成了Select
## 半透明粒子闪烁问题
很大概率是粒子半透明排序问题，半透明排序一直是实现渲染很大的一个问题，其中常用的解决方案是距离排序和index排序，在niagara同一emitter也有这个选项
![](https://pic1.zhimg.com/80/v2-0fd024f24e3059b30e36f55a7b548968_720w.webp
)

在sprite render下面有个这个排序。

view depth：根据深度（是根据camera vectro dot camera direction的值进行排，并不是gbuffer的深度）

view distance：距离相机的距离排序

custom Ascending:根据id排序，越小的id在前面

custom Decending:也是根据进行排序，大的排在前面
![](https://pic1.zhimg.com/80/v2-dbdc92b71fe69d2058d09c1a8547123c_720w.webp
)


越高的数字越靠前，同一数字的话会根据首次排序进行排序，首次排序是根据在创建发射器的时候，就是说这系统里有2个发射器，你复制一个或者新建一个发射器那这个发射器就是排序最前的，数字最大的（首次排序）
![](https://pic4.zhimg.com/80/v2-1552d644466e3969a629b910bd641903_720w.webp
)