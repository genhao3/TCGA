
from genericpath import exists
from torch.utils.data import DataLoader
import random
import torch
import pandas as pd
import torch.utils.data as data
import os
import numpy as np
import math
from sklearn.cluster import KMeans
from PIL import Image
from torchvision import transforms
import warnings
warnings.filterwarnings('ignore')


random.seed(2022)

class TCGAData(data.Dataset):
    def __init__(self, fold,dataset_cfg=None, state=None,n_bins=4,eps=1e-6, patches_path=None):
        self.__dict__.update(locals())
        self.dataset_cfg = dataset_cfg
        self.eps=eps
        self.n_bins=n_bins
        self.state = state
        self.patches_path = patches_path

        self.transform = transforms.Compose([
            transforms.Resize(224),
            transforms.ToTensor(),
            transforms.Normalize(std=(0.5, 0.5, 0.5), mean=(0.5, 0.5, 0.5))])

        self.fold = fold
        if self.dataset_cfg.dataset_name == 'brca_data':
            self.feature_dir= 'send_to_HJQ/FeatureOfPatchSize512/BRCA/pt_files/'
            self.fold_dir= 'dataset_csv/brca'
            self.survival_info_path= 'dataset_csv/tcga_brca_all_clean.csv'
            self.feat_num = 2600# 众数
            # if not self.patches_path is None:
            #     self.survival_info_path = 'dataset_csv/tcga_brca_all_clean_demo.csv'
        elif self.dataset_cfg.dataset_name == 'lusc_data':
            self.feature_dir= 'send_to_HJQ/FeatureOfPatchSize512/LUSC/pt_files/'
            self.fold_dir= 'dataset_csv/lusc'
            self.survival_info_path= '../dataset_csv/tcga_lusc_all_clean.csv'
            self.feat_num = 3000# 众数
            # if not self.patches_path is None:
            #     self.survival_info_path = 'dataset_csv/tcga_lusc_all_clean_demo.csv'
        elif self.dataset_cfg.dataset_name == 'gbm_data':
            self.feature_dir= 'send_to_HJQ/FeatureOfPatchSize512/GBM/pt_files/'
            self.fold_dir= 'dataset_csv/gbm'
            self.survival_info_path= 'dataset_csv/tcga_gbm_all_clean.csv'
            self.feat_num = 2500  # 众数
            if not self.patches_path is None:
                self.survival_info_path = 'dataset_csv/tcga_gbm_all_clean_demo.csv'

        self.csv_dir = self.fold_dir + f'/fold_{self.fold}.csv'

        self.patient_data = pd.read_csv(self.csv_dir)

        self.survival_info = pd.read_csv(self.survival_info_path)
        
        self.get_time_interval()

        self.survival_info.index = self.survival_info['slide_id']

        # self.get_time_interval_60()

        if self.state == 'train':
            self.case_ids = self.patient_data.loc[:, 'train'].dropna()
        elif self.state == 'val':
            self.case_ids = self.patient_data.loc[:, 'val'].dropna()
        elif self.state == 'test':
            self.case_ids = self.patient_data.loc[:, 'test'].dropna()

        # 一个case_id可能对应多个slide_id
        self.survival_data = pd.DataFrame()
        for slide_id in self.survival_info['slide_id']:
            case_id = self.survival_info.loc[slide_id,'case_id']
            exists_pt_path = os.path.exists(os.path.join(self.feature_dir, slide_id.replace('.svs','.pt')))
            if case_id in self.case_ids.values and exists_pt_path:
                self.survival_data = self.survival_data.append(self.survival_info.loc[slide_id])

        self.shuffle = self.dataset_cfg.data_shuffle

    def get_time_interval(self):
        '''
        划分区间
        '''
        
        patients_df = self.survival_info.drop_duplicates(['case_id']).copy()
        uncensored_df = patients_df[patients_df['survival_state'] == 1]

        # 按照数据出现频率百分比划分，比如要把数据分为四份，则四段分别是数据的0-25%，25%-50%，50%-75%，75%-100%，每个间隔段里的元素个数都是相同的
        interval_labels, q_bins = pd.qcut(uncensored_df['survival_months'], q=self.n_bins, retbins=True, labels=False)
        q_bins[-1] = self.survival_info['survival_months'].max() + self.eps
        q_bins[0] = self.survival_info['survival_months'].min() - self.eps

        # 保存病人所属区间信息
        interval_labels, q_bins = pd.cut(patients_df['survival_months'], bins=q_bins, retbins=True, labels=False, right=False, include_lowest=True)
        patients_df.insert(2, 'interval_label', interval_labels.values.astype(int))

        # 相同的病人也保留区间信息
        self.survival_info.index = self.survival_info['case_id']
        patients_df.index = patients_df['case_id']
        for p_id in patients_df['case_id']:
            interval_label = patients_df.loc[p_id,'interval_label']
            self.survival_info.loc[p_id,'interval_label'] = interval_label

    def get_time_interval_60(self):
        '''
        划分区间
        '''
        interval_label = np.ceil(self.survival_info['survival_months'].values)
        interval_label = np.clip(interval_label, 1, 60)-1
        self.survival_info['interval_label'] = interval_label

    def get_nearest_integer(self, A):
        B = int(A)
        mins = float(A - B)
        if mins < 0.5:
            return int(A)
        else:
            return math.ceil(A)  # 将数字向下舍入到最接近的整数

    def bag_generation(self, patches, n_clusters=5):
        kmeans = KMeans(n_clusters=n_clusters)
        kmeans.fit(patches)
        label = kmeans.labels_

        patches_idx = [[] for i in range(n_clusters)]
        for i in range(patches.shape[0]):
            if label[i] == 0:
                patches_idx[0].append(i)
            elif label[i] == 1:
                patches_idx[1].append(i)
            elif label[i] == 2:
                patches_idx[2].append(i)
            elif label[i] == 3:
                patches_idx[3].append(i)
            elif label[i] == 4:
                patches_idx[4].append(i)
            elif label[i] == 5:
                patches_idx[5].append(i)
            elif label[i] == 6:
                patches_idx[6].append(i)
            elif label[i] == 7:
                patches_idx[7].append(i)


        patches_num = []
        for i in range(n_clusters):
            patches_num.append(len(patches_idx[i]))

        '''generate bag According to formula (4)'''
        patches_get_num = []
        mask = np.ones(n_clusters, dtype=np.float32)
        for i in range(n_clusters):
            patch_get_num = self.get_nearest_integer(10 * (patches_num[i] / patches.shape[0]))
            patches_get_num.append(patch_get_num)
            '''get mask, if cluster_i have no patches, then mask_i=0'''
            if patch_get_num == 0:
                mask[i] = 0
        return patches_idx, patches_get_num

    def __len__(self):
        return len(self.survival_data)

    def __getitem__(self, idx):
        label_series = self.survival_data.iloc[[idx]]
        survival_time = label_series['survival_months'].values[0]
        state_label = 1 - label_series['survival_state'].values[0]
        interval_label = label_series['interval_label'].values[0]
        slide_id = os.path.splitext(','.join(label_series['slide_id'].values))[0]  # array --> str --> 去后缀

        feat_file = os.path.join(self.feature_dir, slide_id) + '.pt'
        # features = pd.read_csv(feat_file).values
        features = torch.load(feat_file)

        # ----> shuffle
        if self.shuffle == True and self.state == 'train':
            index = [x for x in range(features.shape[0])]
            random.shuffle(index)
            features = features[index]


        if not self.feat_num is None:
            if features.shape[0] >= self.feat_num:
                features_vec = features[:self.feat_num, :]
            else:  # 不够的，重复地补
                features_vec = features
                cha = self.feat_num - features.shape[0]
                shang = cha // features.shape[0]
                yu = cha % features.shape[0]
                for sh in range(shang):
                    features_vec = torch.cat([features_vec,features],dim=0)
                if yu > 0:
                    features_vec = torch.cat([features_vec,features[:yu,:]],dim=0)
        else:
            features_vec = torch.from_numpy(features)

        "为BDOCOX写"
        if not self.patches_path is None:
            # 不根据self.feat_num补
            if features.shape[0] >= self.feat_num:
                features_vec = features[:self.feat_num, :]
            else:
                features_vec = features

            # 如果要获取BDOCOX的输入们，则需要补充处理，根据聚类结果重新获得patches图，将构建的包
            patches_idx, get_patches_num = self.bag_generation(patches=features_vec,
                                                               n_clusters=self.dataset_cfg.BDOCOX.cluster_num)

            total_bag = []
            for bag_i in range(self.dataset_cfg.BDOCOX.bag_num):  # 共有self.dataset_cfg.BDOCOX.bag_num个bag
                # 逐个逐个获得bag中的instance
                bag = []
                for i, num in enumerate(get_patches_num):  # 共有5个clusters，循环5次，每次获得的instance放在bag_i中
                    if num == 0:
                        continue

                    feat = []
                    for j in range(num):
                        rd = random.randint(0, len(patches_idx[i]) - 1)  # 获得一个随机数，这个随机数是用于选择patches_idx[i]元素的索引
                        p_idx = patches_idx[i][rd]
                        png = Image.open(os.path.join(self.patches_path, slide_id, str(p_idx) + '.png'))
                        png = self.transform(png)
                        feat.append(png)

                    bag.append(torch.stack(feat, dim=0))
                features_vec = torch.concat(bag, dim=0)
                total_bag.append(features_vec)

            survival_time = survival_time.repeat(self.dataset_cfg.BDOCOX.bag_num)
            state_label = state_label.repeat(self.dataset_cfg.BDOCOX.bag_num)
            interval_label = interval_label.repeat(self.dataset_cfg.BDOCOX.bag_num)
            # slide_id = slide_id * self.dataset_cfg.BDOCOX.bag_num
            return torch.stack(total_bag, dim=0), survival_time, state_label, interval_label, slide_id


        return features_vec, survival_time, state_label, interval_label,slide_id


if __name__ == '__main__':
    import argparse
    from utils.utils import read_yaml
    import os
    import shutil
    from pathlib import Path
    from tqdm import tqdm


    def make_parse():
        parser = argparse.ArgumentParser()
        parser.add_argument('--stage', default='train', type=str)
        parser.add_argument('--config', default='../config/config.yaml', type=str)
        parser.add_argument('--gpus', default=[0])
        parser.add_argument('--fold', default=0)
        args = parser.parse_args()
        return args

    args = make_parse()
    cfg = read_yaml(args.config)


    def mkfile(file):
        if not os.path.exists(file):
            os.makedirs(file)

    "用GBM50例构建了一个小数据集，用于写BDOCOX网络"
    get_slid_name_file = '../GBM_svs_and_coords/GBM_50_case_svs/50case/'
    case_names = os.listdir(get_slid_name_file)

    "修改tcga_gbm_all_clean.csv文件，只放小数据集的信息，其他的删除"
    ori_gbm = '../dataset_csv/tcga_gbm_all_clean.csv'
    new_gbm = '../dataset_csv/tcga_gbm_all_clean_demo.csv'
    if not os.path.exists(new_gbm):

        ori_gbm_csv = pd.read_csv(ori_gbm)
        new_survival_data = pd.DataFrame()
        for case in tqdm(case_names):
            slide = [Path(x).stem for x in os.listdir(get_slid_name_file + case) if Path(x).suffix == '.svs']
            if slide[0] + '.svs' in ori_gbm_csv["slide_id"].tolist():
                raw_name = slide[0] + '.svs'
                new_survival_data = new_survival_data.append(ori_gbm_csv.loc[ori_gbm_csv.slide_id == raw_name])
        print('new_survival_data:\n', new_survival_data)
        new_survival_data.to_csv(new_gbm, index=False)
    else:
        print('pass new tcga_gbm_all_clean_demo.')
        pass

    LuscDataset = TCGAData(fold="0", dataset_cfg=cfg.General, state='train', patches_path=cfg.BDOCOX.patches_path)
    # LuscDataset = TCGAData(fold="0", dataset_cfg=cfg.General, state='train')
    dataloader = DataLoader(LuscDataset, batch_size=1, num_workers=4, shuffle=False)
    for idx, data in enumerate(dataloader):
        print('feature:', data[0].shape)
        print('survival_label:', data[1].shape, data[1])
        print('censorship_label:', data[2].shape, data[2])
        print('slide_id:', data[3].shape, data[3])
        break

    # LuscDataset = TCGAData(fold="0", dataset_cfg=cfg.Data, state='train')
    # # dataloader打乱的是wsi的顺序，data_shuffle打乱的是patches的顺序
    # dataloader = DataLoader(LuscDataset, batch_size=8, num_workers=8, shuffle=False)
    # for idx, data in enumerate(dataloader):
    #     print('feature:', data[0].shape)  # [8, 3000, 1024]
    #     print('feature:', data[0].dtype)
    #     print('survival_label:', data[1])
    #     print('censorship_label:', data[2])
    #     print('slide_id:', data[3])
    #     break