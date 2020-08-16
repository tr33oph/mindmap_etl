from mindmap_etl.extractor import extract_edges, extract_nodes


def extract_from_df(df, node_extractors, edge_extractors, 
        pre_extractor=lambda x:x, format_type_func=None,format_id_func=None):
    
    for idx, row in df.iterrows():

        row = pre_extractor(row)
        nodes = extract_nodes(idx, row, node_extractors, format_type_func=format_type_func)
        
        nodes = {k:v for k,v in nodes.items()
                    if v['properties'][node_extractors[k]['schema']['pk']]}

        edges = extract_edges(idx, row, nodes, edge_extractors, format_id_func=format_id_func)
        for i in edges:
            edges[i]['properties'] = {}
        yield (list(nodes.values()), list(edges.values()))
