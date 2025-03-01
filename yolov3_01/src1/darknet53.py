import torch
from torch import nn,Tensor

class UpsampleLayer(torch.nn.Module):

    def __init__(self):
        super(UpsampleLayer, self).__init__()

    def forward(self, x):
        return torch.nn.functional.interpolate(x, scale_factor=2, mode='nearest')


class ConvolutionalLayer(torch.nn.Module):

    def __init__(self, in_channels, out_channels, kernel_size, stride, padding, bias=False):
        super(ConvolutionalLayer, self).__init__()

        self.sub_module = torch.nn.Sequential(
            torch.nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=bias),
            torch.nn.BatchNorm2d(out_channels),
            torch.nn.LeakyReLU(0.1,inplace=True)
        )

    def forward(self, x):
        return self.sub_module(x)


class ResidualLayer(torch.nn.Module):

    def __init__(self, in_channels):
        super(ResidualLayer, self).__init__()

        self.sub_module = torch.nn.Sequential(
            ConvolutionalLayer(in_channels, in_channels // 2, 1, 1, 0),
            ConvolutionalLayer(in_channels // 2, in_channels, 3, 1, 1),
        )

    def forward(self, x):
        return x + self.sub_module(x)


class DownsamplingLayer(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super(DownsamplingLayer, self).__init__()

        self.sub_module = torch.nn.Sequential(
            ConvolutionalLayer(in_channels, out_channels, 3, 2, 1)
        )

    def forward(self, x):
        return self.sub_module(x)


class ConvolutionalSet(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ConvolutionalSet, self).__init__()

        self.sub_module = torch.nn.Sequential(
            ConvolutionalLayer(in_channels, out_channels, 1, 1, 0),
            ConvolutionalLayer(out_channels, in_channels, 3, 1, 1),

            ConvolutionalLayer(in_channels, out_channels, 1, 1, 0),
            ConvolutionalLayer(out_channels, in_channels, 3, 1, 1),

            ConvolutionalLayer(in_channels, out_channels, 1, 1, 0),
        )
        # print(in_channels, out_channels)

    def forward(self, x):
        return self.sub_module(x)


class ConvolutionalSets(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ConvolutionalSets, self).__init__()

        self.sub_module = torch.nn.Sequential(
            ConvolutionalLayer(in_channels, out_channels, 3, 1, 1),
            ConvolutionalLayer(out_channels, in_channels, 1, 1, 0),

            ConvolutionalLayer(in_channels, out_channels, 3, 1, 1),
            ConvolutionalLayer(out_channels, in_channels, 1, 1, 0),


        )
        # print(in_channels, out_channels)

    def forward(self, x):
        return self.sub_module(x)

class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
    def paraminit(self):
        for param in self.parameters():
            nn.init.normal_(param, mean=0, std=0.1)
    def forward(self, *input:Tensor) -> Tensor:
        raise NotImplementedError

class MainNet(Net):

    def __init__(self, cls_num):
        super(MainNet, self).__init__()

        self.trunk_52 = torch.nn.Sequential(
            ConvolutionalLayer(3, 32, 3, 1, 1),
            ConvolutionalLayer(32, 64, 3, 2, 1),

            ResidualLayer(64),
            DownsamplingLayer(64, 128),

            ResidualLayer(128),
            ResidualLayer(128),
            DownsamplingLayer(128, 256),

            ResidualLayer(256),
            ResidualLayer(256),
            ResidualLayer(256),
            ResidualLayer(256),
            ResidualLayer(256),
            ResidualLayer(256),
            ResidualLayer(256),
            ResidualLayer(256),
        )

        self.trunk_26 = torch.nn.Sequential(
            DownsamplingLayer(256, 512),
            ResidualLayer(512),
            ResidualLayer(512),
            ResidualLayer(512),
            ResidualLayer(512),
            ResidualLayer(512),
            ResidualLayer(512),
            ResidualLayer(512),
            ResidualLayer(512),
        )

        self.trunk_13 = torch.nn.Sequential(
            DownsamplingLayer(512, 1024),
            ResidualLayer(1024),
            ResidualLayer(1024),
            ResidualLayer(1024),
            ResidualLayer(1024)
        )

        self.convset_13 = torch.nn.Sequential(
            ConvolutionalSet(1024, 512)
        )

        self.detetion_13 = torch.nn.Sequential(
            ConvolutionalLayer(512, 1024, 3, 1, 1),
            torch.nn.Conv2d(1024, 3 * (5 + cls_num), 1, 1, 0)
        )

        self.up_26 = torch.nn.Sequential(
            ConvolutionalLayer(512, 256, 1, 1, 0),#
            UpsampleLayer()
        )

        self.convset_26 = torch.nn.Sequential(
            ConvolutionalLayer(768, 256, 1, 1, 0),
            ConvolutionalSets(256, 512)
        )

        self.detetion_26 = torch.nn.Sequential(
            ConvolutionalLayer(256, 512, 3, 1, 1),
            torch.nn.Conv2d(512, 3 * (5 + cls_num), 1, 1, 0)
        )

        self.up_52 = torch.nn.Sequential(
            ConvolutionalLayer(256, 128, 1, 1, 0),#
            UpsampleLayer()
        )

        self.convset_52 = torch.nn.Sequential(
            ConvolutionalLayer(384, 128, 1, 1, 0),
            ConvolutionalSets(128, 256)
        )

        self.detetion_52 = torch.nn.Sequential(
            ConvolutionalLayer(128, 256, 3, 1, 1),
            torch.nn.Conv2d(256, 3 * (5 + cls_num), 1, 1, 0)
        )

    def forward(self, x):
        h_52 = self.trunk_52(x)
        h_26 = self.trunk_26(h_52)
        h_13 = self.trunk_13(h_26)

        convset_out_13 = self.convset_13(h_13)
        detetion_out_13 = self.detetion_13(convset_out_13)

        up_out_26 = self.up_26(convset_out_13)
        route_out_26 = torch.cat((up_out_26, h_26), dim=1)
        convset_out_26 = self.convset_26(route_out_26)
        detetion_out_26 = self.detetion_26(convset_out_26)

        up_out_52 = self.up_52(convset_out_26)
        route_out_52 = torch.cat((up_out_52, h_52), dim=1)
        convset_out_52 = self.convset_52(route_out_52)
        detetion_out_52 = self.detetion_52(convset_out_52)

        return detetion_out_13, detetion_out_26, detetion_out_52


if __name__ == '__main__':
    net = MainNet(80)
    # layer89_conv_89 = net.convset_26[0].sub_module[2].sub_module[0]
    # print(layer89_conv_89)

    # print(net)

    import cv2
    # net.cuda().half()
    # x = torch.cuda.HalfTensor(2, 3, 416, 416)
    x = torch.randn(2,3,416,416)

        #
    y_13, y_26, y_52 = net(x)
    print(y_13.shape)
    # # print(y_26.shape)
        # # print(y_52.shape)
        # print(y_13.view(-1, 3, 5, 13, 13).shape)
    # torch.save(net.state_dict(),
    #            './darknet.pt')
    #
    # weights = torch.load("yolov3.pt")['model']
    # layer0 = net.trunk_52[0].sub_module[0]
    # # print(layer0)
    # layer0.weight.data = weights['module_list.0.conv_0.weight']
    # # print(layer0.weight.data)
    # layer1 = net.trunk_52[0].sub_module[1]
    # # print(layer1)
    # layer1.weight.data = weights['module_list.0.batch_norm_0.bias']
    # # print(layer1.weight.data )
    # cv2.waitKey(0)
    print(net.trunk_52[0].sub_module[0])
    print(net.trunk_52[2].sub_module[0])

