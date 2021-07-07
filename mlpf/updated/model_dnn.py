import numpy as np
import mplhep

import torch
import torch_geometric

import torch.nn as nn
import torch.nn.functional as F
import torch_geometric.transforms as T
from torch_geometric.nn import EdgeConv, MessagePassing, EdgePooling, GATConv, GCNConv, JumpingKnowledge, GraphUNet, DynamicEdgeConv, DenseGCNConv
from torch_geometric.nn import TopKPooling, SAGPooling, SGConv
from torch.nn import Sequential as Seq, Linear as Lin, ReLU
from torch_scatter import scatter_mean
from torch_geometric.nn.inits import reset
from torch_geometric.data import Data, DataLoader, DataListLoader, Batch
from torch.utils.data import random_split

#from torch_geometric.nn import GravNetConv         # if you want to get it from source code (won't be able to retrieve the adjacency matrix)
from gravnet import GravNetConv
from torch_geometric.nn import GraphConv

#Model with gravnet clustering
class PFNet7(nn.Module):
    def __init__(self,
        input_dim=12, hidden_dim=256, hidden_dim_nn1=64, input_encoding=12, encoding_dim=64,
        output_dim_id=6,
        output_dim_p4=6,
        space_dim=8, propagate_dimensions=22, nearest=40,
        target="gen", nn1=True, conv2=True, nn3=True, nn4=True):

        super(PFNet7, self).__init__()

        self.target = target
        self.nn1 = nn1
        self.conv2 = conv2
        self.nn3 = nn3
        self.nn4 = nn4

        self.act = nn.LeakyReLU
        self.act_f = torch.nn.functional.leaky_relu
        self.act_tanh = torch.nn.Tanh

        # (1) DNN
        self.nn1 = nn.Sequential(
            nn.Linear(input_dim, hidden_dim_nn1),
            self.act(0.5),
            nn.Linear(hidden_dim_nn1, hidden_dim_nn1),
            self.act(0.5),
            nn.Linear(hidden_dim_nn1, hidden_dim_nn1),
            self.act(0.5),
        )

        self.nn2 = nn.Sequential(
            nn.Linear(hidden_dim_nn1 + input_dim, hidden_dim),
            self.act(0.5),
            nn.Linear(hidden_dim, hidden_dim),
            self.act(0.5),
            nn.Linear(hidden_dim, hidden_dim),
            self.act(0.5),
            nn.Linear(hidden_dim, output_dim_id),
        )

        # (5) DNN layer: regressing p4
        self.nn3 = nn.Sequential(
            nn.Linear(encoding_dim + output_dim_id + input_dim, hidden_dim),
            self.act(0.5),
            nn.Linear(hidden_dim, hidden_dim),
            self.act(0.5),
            nn.Linear(hidden_dim, hidden_dim),
            self.act(0.5),
            nn.Linear(hidden_dim, hidden_dim),
            self.act(0.5),
        )

        self.nn4 = nn.Sequential(
            nn.Linear(hidden_dim + output_dim_id + input_dim, hidden_dim),
            self.act(0.5),
            nn.Linear(hidden_dim, hidden_dim),
            self.act(0.5),
            nn.Linear(hidden_dim, hidden_dim),
            self.act(0.5),
            nn.Linear(hidden_dim, output_dim_p4),
        )

    def forward(self, data):

        x0 = data.x

        # Encoder/Decoder step
        if self.nn1:
            x = self.nn1(x0)

        # DNN to predict PID
        pred_ids = self.nn2(torch.cat([x, x0], axis=-1))

        # DNN to predict p4
        if self.nn3:
            nn3_input = torch.cat([x, pred_ids, x0], axis=-1)
            pred_p4 = self.nn3(nn3_input)
        else:
            pred_p4=torch.zeros_like(data.ycand)

        if self.nn4:
            nn3_input = torch.cat([pred_p4, pred_ids, x0], axis=-1)
            pred_p4 = self.nn4(nn3_input)
        else:
            pred_p4=torch.zeros_like(data.ycand)

        return pred_ids, pred_p4, data.ygen_id, data.ygen, data.ycand_id, data.ycand

# -------------------------------------------------------------------------------------
# # uncomment to test a forward pass
# from graph_data_delphes import PFGraphDataset
# from data_preprocessing import data_to_loader_ttbar
# from data_preprocessing import data_to_loader_qcd
# 
# full_dataset = PFGraphDataset('../../test_tmp_delphes/data/pythia8_ttbar')
#
# train_loader, valid_loader = data_to_loader_ttbar(full_dataset, n_train=2, n_valid=1, batch_size=2)
#
# print('Input to the network:', next(iter(train_loader)))
#
# model = PFNet7()
#
# for batch in train_loader:
#     pred_ids, pred_p4, target_ids, target_p4, cand_ids, cand_p4 = model(batch)
#     break
