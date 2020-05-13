# Copyright <2020> <Chen Wang <https://chenwang.site>, Carnegie Mellon University>

# Redistribution and use in source and binary forms, with or without modification, are 
# permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this list of 
# conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice, this list 
# of conditions and the following disclaimer in the documentation and/or other materials 
# provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its contributors may be 
# used to endorse or promote products derived from this software without specific prior 
# written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY 
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES 
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT 
# SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, 
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED 
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN 
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH 
# DAMAGE.

import os
import tqdm
import copy
import torch
import os.path
import argparse
import numpy as np
import torch.nn as nn
from models import Net
import torch.utils.data as Data
from datasets import Citation, citation_collate


def performance(loader, net):
    correct, total = 0, 0
    with torch.no_grad():
        for batch_idx, (inputs, targets, neighbor) in enumerate(loader):
            if torch.cuda.is_available():
                inputs, targets, neighbor = inputs.cuda(), targets.cuda(), [item.cuda() for item in neighbor]
            outputs = net(inputs, neighbor)
            _, predicted = torch.max(outputs.data, 1)
            total += targets.size(0)
            correct += predicted.eq(targets.data).cpu().sum().item()
        acc = 100.*correct/total
    return acc


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == '__main__':
    # Arguements
    parser = argparse.ArgumentParser(description='Feature Graph Networks')
    parser.add_argument("--data-root", type=str, default='/data/datasets', help="learning rate")
    parser.add_argument("--dataset", type=str, default='cora', help="dataset name")
    parser.add_argument("--lr", type=float, default=0.1, help="learning rate")
    parser.add_argument("--batch-size", type=int, default=10, help="number of minibatch size")
    parser.add_argument("--iteration", type=int, default=3, help="number of training iteration")
    parser.add_argument("--memory-size", type=int, default=10, help="number of samples")
    parser.add_argument("--momentum", type=float, default=0, help="momentum of SGD optimizer")
    parser.add_argument("--adj-momentum", type=float, default=0, help="momentum of the feature adjacency")
    parser.add_argument('--seed', type=int, default=1, help='Random seed.')
    args = parser.parse_args(); print(args)
    torch.manual_seed(args.seed)

    train_data = Citation(root=args.data_root, name=args.dataset, data_type='train', download=True)
    val_data = Citation(root=args.data_root, name=args.dataset, data_type='val', download=True)
    train_loader = Data.DataLoader(dataset=train_data, batch_size=args.batch_size, shuffle=True, collate_fn=citation_collate)
    val_loader = Data.DataLoader(dataset=val_data, batch_size=args.batch_size, shuffle=False, collate_fn=citation_collate)

    net = Net(args).cuda() if torch.cuda.is_available() else Net(args)
    for batch_idx, (inputs, targets, neighbor) in enumerate(train_loader):
        if torch.cuda.is_available():
            inputs, targets, neighbor = inputs.cuda(), targets.cuda(), [item.cuda() for item in neighbor]
        net.observe(inputs, targets, neighbor)
        if batch_idx % 10 == 0:
            val_acc = performance(val_loader, net)
            print('val_acc: %.2f in %d batch'%(val_acc, batch_idx))

    # train_loss, train_acc = train(train_loader, net, criterion, optimizer)
    test_data = Citation(root=args.data_root, name=args.dataset, data_type='test', download=True)
    test_loader = Data.DataLoader(dataset=test_data, batch_size=args.batch_size, shuffle=False, collate_fn=citation_collate)
    train_acc, val_acc, test_acc = performance(train_loader, net), performance(val_loader, net), performance(test_loader, net)
    print('train_acc: %.2f, val_acc: %.2f, test_acc: %.2f'%(train_acc, val_acc, test_acc))
    print('number of parameters:', count_parameters(net))
