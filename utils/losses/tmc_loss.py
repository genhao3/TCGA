import torch
import numpy as np
from pycox.models.utils import pad_col

class TMCLoss(object):

    def __init__(self, beta=1,alpha_ij=0.5,alpha_i=0.25,alpha_j=0.25):
        pass

    def __call__(self, results_dict, survival_time, state_label,interval_label,eps=1e-7):
        # This calculation credit to Travers Ching https://github.com/traversc/cox-nnet
        # Cox-nnet: An artificial neural network method for prognosis prediction of high-throughput omics data
        
       
        return 0