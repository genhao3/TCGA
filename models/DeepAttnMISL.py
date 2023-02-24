"""
Model definition of DeepAttnMISL

If this work is useful for your research, please consider to cite our papers:

[1] "Whole Slide Images based Cancer Survival Prediction using Attention Guided Deep Multiple Instance Learning Networks"
Jiawen Yao, XinliangZhu, Jitendra Jonnagaddala, NicholasHawkins, Junzhou Huang,
Medical Image Analysis, Available online 19 July 2020, 101789

[2] "Deep Multi-instance Learning for Survival Prediction from Whole Slide Images", In MICCAI 2019

"""

import torch.nn as nn
import torch
import math
import numpy as np
import random
# from sklearn.cluster import KMeans
from torch_kmeans import KMeans
import warnings

warnings.filterwarnings('ignore')
from time import time
from kmeans_pytorch import kmeans, kmeans_predict


def get_nearest_integer(A):
    # 应该是公式(4)
    B = int(A)
    mins = float(A - B)
    if mins < 0.5:
        return int(A)
    else:
        return math.ceil(A)  # 将数字向下舍入到最接近的整数





class DeepAttnMIL_Surv(nn.Module):
    """
    Deep AttnMISL Model definition
    """

    def __init__(self, cluster_num, n_classes, device=torch.device('cpu')):
        super(DeepAttnMIL_Surv, self).__init__()
        self.device = device

        self.embedding_net = nn.Sequential(nn.Conv2d(1024, 64, 1),  # 1 ×1 conv layer
                                           nn.ReLU(),
                                           nn.AdaptiveAvgPool2d((1, 1))
                                           )

        self.attention = nn.Sequential(
            nn.Linear(64, 32),  # V
            nn.Tanh(),
            nn.Linear(32, 1)  # W
        )

        self.fc6 = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(p=0.5),
            nn.Linear(32, n_classes)
        )
        self.cluster_num = cluster_num

    def masked_softmax(self, x, mask=None):
        """
        Performs masked softmax, as simply masking post-softmax can be
        inaccurate
        :param x: [batch_size, num_items]
        :param mask: [batch_size, num_items]
        :return:
        """
        if mask is not None:
            mask = mask.float()
        if mask is not None:
            x_masked = x * mask + (1 - 1 / (mask + 1e-5))
        else:
            x_masked = x
        x_max = x_masked.max(1)[0]
        x_exp = (x - x_max.unsqueeze(-1)).exp()
        if mask is not None:
            x_exp = x_exp * mask.float()
        return x_exp / x_exp.sum(1).unsqueeze(-1)

    def bag_generation(self, patches):
        # kmeans_ = KMeans(n_clusters=n_clusters)
        # kmeans_.fit(patches.cpu())
        # label = kmeans_.labels_  # 这outputs中每个样本的标签[0 0 2 4 4 0 2 2 1 0 1 4 1 3 3 0 2 1 0 2]

        # jinqi: use gpu
        # https://github.com/subhadarship/kmeans_pytorch
        # label, cluster_centers = kmeans(X=patches, num_clusters=n_clusters, distance='euclidean', device=device)

        # https://github.com/jokofa/torch_kmeans
        kmeans = KMeans(n_clusters=self.cluster_num, verbose=False).to(self.device)
        result = kmeans(patches.unsqueeze(0))
        label = result.labels.squeeze()

        # print(patches.shape[0])
        clusters = []
        # clusters = torch.FloatTensor().cuda()
        for label_idx in range(self.cluster_num):
            # 提取指定值label_idx的索引
            # selected_idx = torch.squeeze(torch.nonzero(torch.from_numpy(label).to(device) == label_idx))
            selected_idx = torch.squeeze(torch.nonzero(label.cuda() == label_idx))
            # 根据索引提取tensor patches中的值
            patches_idx = torch.index_select(patches, 0, selected_idx)
            # 按0-cluster_num
            clusters.append(patches_idx)

        # 循环，占用cpu
        # for i in range(cluster_num):
        #     cluster = []
        #     clusters.append(cluster)
        # clusters = [[] for i in range(cluster_num)]
        # for i in range(patches.shape[0]):
        #     if label[i] == 0:
        #         clusters[0].append((patches[i]))
        #     elif label[i] == 1:
        #         clusters[1].append(patches[i])
        #     elif label[i] == 2:
        #         clusters[2].append(patches[i])
        #     elif label[i] == 3:
        #         clusters[3].append(patches[i])
        #     elif label[i] == 4:
        #         clusters[4].append(patches[i])
        #     elif label[i] == 5:
        #         clusters[5].append(patches[i])
        #     elif label[i] == 6:
        #         clusters[6].append(patches[i])
        #     elif label[i] == 7:
        #         clusters[7].append(patches[i])
        # clusters = [torch.stack(cc) for cc in clusters]

        patches_num = []
        mask = torch.ones(self.cluster_num, dtype=torch.float32, device=self.device)
        for i in range(self.cluster_num):
            patches_num.append(len(clusters[i]))
            '''get mask, if cluster_i have no patches, then mask_i=0'''
            if len(clusters[i]) == 0:
                mask[i] = 0

        return clusters, mask

    def forward(self, data):

        bs_out = []
        for bs in range(data.shape[0]):
            x, mask = self.bag_generation(data[bs])

            "Q:x里面的每个bag的patches不一致，要如何组成batch呢？x里面的bag shape [num_patches, 1024]"
            "A:作者代码里写了，batchsize必须是1"

            " x is a tensor list"
            # 计算每个簇/bag的embedding
            res = []
            for i in range(self.cluster_num):
                # embedding_net的输入是[bs, feat-dim, num_patches, 1]
                hh = x[i].permute(1, 0)
                hh = hh[None, :, :, None]
                output = self.embedding_net(hh)
                output = output.view(output.size()[0], -1)
                res.append(output)

            h = torch.cat(res)

            b = h.size(0)
            c = h.size(1)

            h = h.view(b, c)

            A = self.attention(h)
            A = torch.transpose(A, 1, 0)  # KxN

            A = self.masked_softmax(A, mask.to(self.device))

            M = torch.mm(A, h)  # KxL

            Y_pred = self.fc6(M)

            bs_out.append(Y_pred)

        results_dict = {'logits': torch.concat(bs_out, dim=0)}  # , 'Y_prob': Y_prob, 'Y_hat': Y_hat}

        return results_dict


def setup_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


if __name__ == '__main__':
    import os

    os.environ["CUDA_VISIBLE_DEVICES"] = '6'
    setup_seed(2022)

    model = DeepAttnMIL_Surv(cluster_num=6, n_classes=1, device=torch.device('cuda')).cuda()
    # 6个簇，每个簇有100个示例，每个示例是1024-dim的embedding vector
    x = torch.randn([16, 3000, 1024]).cuda()
    y = model(x)
    print(y['logits'].shape)
    print(y['logits'])
