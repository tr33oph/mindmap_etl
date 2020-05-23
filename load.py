# coding: utf-8
from schema_parse import to_attr_dict, read, extract_shape_rels
import json
from extractor import extract_nodes, extract_edges

def pre_extractor(row):
    return row

p = './etl.xmmap'

(origin, node_schemas, edge_schemas, node_extractors, edge_extractors) = extract_shape_rels(p)

import pandas as pd

df = pd.read_csv('test_mmap_loader.csv')

for idx, row in df.fillna('').iterrows():
    row = pre_extractor(row)
    nodes = extract_nodes(idx, row, node_extractors)
    print(nodes)
    edges = extract_edges(idx, row, nodes, edge_extractors)
    print(edges)
