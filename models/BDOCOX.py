import math
import pandas as pd
import torch
import torchvision
import numpy as np
import random
from sklearn.cluster import KMeans
from torch import nn
import os
import warnings
warnings.filterwarnings('ignore')
os.environ["OMP_NUM_THREADS"] = '1'


class BDOCOX(nn.Module):
    """
    Model definition
    """

    def __init__(self, cluster_num=6, n_classes=1, bag_num=20):
        super(BDOCOX, self).__init__()
        self.cluster_num = cluster_num
        self.bag_num = bag_num

        # 这三个layer的输入是224*224的patches图片，而不是已经经过encoder特征提取的featre vector
        self.layer1 = nn.Sequential(nn.Conv2d(in_channels=3, out_channels=32, kernel_size=7, stride=3),
                                    nn.BatchNorm2d(32),
                                    nn.ReLU(),
                                    nn.MaxPool2d(2)
                                    )
        self.layer2 = nn.Sequential(nn.Conv2d(in_channels=32, out_channels=32, kernel_size=5, stride=2),
                                    nn.BatchNorm2d(32),
                                    nn.ReLU(),
                                    nn.MaxPool2d(2)
                                    )
        self.layer3 = nn.Sequential(nn.Conv2d(in_channels=32, out_channels=32, kernel_size=3, stride=2),
                                    nn.BatchNorm2d(32),
                                    nn.ReLU(),
                                    nn.MaxPool2d(2)
                                    )


        self.fc = nn.Sequential(
            # nn.Linear(1024, 16),
            # nn.ReLU(),
            # nn.Dropout(p=0.5),
            nn.Linear(32, n_classes)
        )

    def forward(self, data):
        bag = []
        for i in range(data.shape[0]):
            x = data[i]

            x= self.layer1(x)
            # print('x1:{}'.format(x.shape))
            x= self.layer2(x)
            # print('x2:{}'.format(x.shape))
            x= self.layer3(x)
            # print('x3:{}'.format(x.shape))
            x = torch.flatten(x, start_dim=1)
            # print('x4:{}'.format(x.shape))
            Y_pred = self.fc(x)
            # print('Y_pred:{}'.format(Y_pred.shape))
            bag.append(Y_pred)

        out = torch.stack(bag, dim=0).mean(axis=1)  # 公式(5)上面的一段话：对bag中的每个instance取平均，得到每个bag的预测结果
        results_dict = {'logits': out}  #, 'Y_prob': Y_prob, 'Y_hat': Y_hat}

        return results_dict



if __name__ == '__main__':
    model = BDOCOX(cluster_num=6, n_classes=4, bag_num=20)
    x = torch.randn([20, 10, 3, 224, 224])
    y = model(x)
    print(y['logits'].shape)

    # a = get_nearest_integer(1.55)
    # print(a)
    # print(round(1.55))
