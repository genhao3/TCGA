import torch
from utils.losses.cox_loss import CoxLoss


def get_I(label_os, label_oss, i, j):
    if label_oss[i] == 1:
        if label_oss[j] != 0:
            if label_os[i] < label_os[j]:
                return 1
            else:
                return 0
        else:
            return 0
    else:
        return 0


def Ranking_Loss(predict, label_os, label_oss):
    '''
        参考论文公式(4-2)
        predict:预测的风险  f (x) =αT*x is being called as risk function 风险函数 αT*x  猜测α为单位矩阵
        label_os:随访时间或死亡时间  t
        label_oss:是否发生损伤  non-censored or censored  δ
        '''

    predict = predict['logits']
    # 求每个bag里面提取出所有向量的平均值
    predict = torch.sum(predict, dim=1) / predict.shape[1]

    # 在Batch Size 获取降序的索引
    index = torch.argsort(label_os, dim=0, descending=True)

    # 匹配降序的索引
    risk = torch.gather(input=predict, dim=0, index=index)  # 根据OS的降序  改变predict、oss的顺序    因为患者的生存时间与风险值不对应
    label_state = torch.gather(input=label_oss, dim=0, index=index)

    # 风险比率  the hazard ratio
    hazard_ratio = torch.exp(risk)

    whole_loss = 0

    for i in range(predict.shape[0]):
        for j in range(predict.shape[0]):
            if i != j:
                I = get_I(label_os, label_oss, i, j)
                if I != 0:
                    r = hazard_ratio[i] / hazard_ratio[j]
                    max = 1 - r if r <= 1 else r - 1
                    temp_loss = I * max
                    whole_loss += temp_loss

    # 合并a,b两个tensor a>0的地方保存，防止分母为0
    # 如果全为负样本，0->1e-7
    num_observed_events = torch.sum(label_state)
    num_observed_events = num_observed_events.float()
    num_observed_events = torch.where(num_observed_events > 0, num_observed_events,
                                      torch.tensor(1e-7, device=num_observed_events.device, ))

    # 类似除以batch size
    loss = -whole_loss / num_observed_events
    return loss


class CoxRankingLoss(object):
    def __init__(self, regularization_parameter=10):
        self.regularization_parameter = regularization_parameter
        self.coxloss = CoxLoss()

    def __call__(self, predict, label_os, label_oss, interval_label):
        # This calculation credit to Travers Ching https://github.com/traversc/cox-nnet
        # Cox-nnet: An artificial neural network method for prognosis prediction of high-throughput omics data
        whole_loss = self.coxloss(predict, label_os, label_oss, None) \
                     + self.regularization_parameter * Ranking_Loss(predict, label_os, label_oss)
        return whole_loss


if __name__ == '__main__':
    predict= {}
    predict['logits'] = torch.tensor([[0.9648], [0.6544], [0.5468], [0.1354]], device='cuda:0', dtype=torch.float16).cuda()
    predict['logits'].requires_grad_(True)
    print(predict['logits'].shape)

    label_os = torch.tensor([69.3333,  20.0000, 121.2000,   6.7333], device='cuda:0', dtype=torch.float64)
    print(label_os)
    label_oss = torch.tensor([1, 1, 1, 0], device='cuda:0')

    loss_func = CoxRankingLoss()
    loss = loss_func(predict, label_os.cuda(), label_oss.cuda())
    print(loss)
    loss.requires_grad_(True)
    loss.backward()