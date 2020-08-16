import time
from hugegraph.api import Hugegraph
from mindmap_etl.schema_parse import extract_shape_rels

def add_schemas(hg: Hugegraph, schema_path):
    (
        origin, node_schemas, edge_schemas,
        node_extractors, edge_extractors
    ) = extract_shape_rels(schema_path)
    add_node_schemas(hg, node_schemas)
    add_edge_schema(hg, edge_schemas)
    return origin, node_schemas, edge_schemas, node_extractors, edge_extractors

def add_node_schemas(hg: Hugegraph, node_schemas):
    for name in node_schemas:
        fmap = node_schemas[name]['fields']
        for fname, dtype_dict in fmap.items():
            hg.schema.add_propertykey_ign(fname, data_type=dtype_dict['dtype'])
        
        if node_schemas[name].get('pk', None):
            hg.schema.add_vertexlabel_ign(
                name,
                properties=list(fmap.keys()),
                id_strategy='PRIMARY_KEY',
                primary_keys=[node_schemas[name]['pk']],
                nullable_keys = [v['name'] for v in fmap.values() if v['nullable']]
            )
            
def add_edge_schema(hg: Hugegraph, edge_schemas):
    for name,v in edge_schemas.items():
        hg.schema.add_edgelabel_ign(
            name,
            source_label=v['from']['name'],
            target_label=v['to']['name'],
            properties=[])


def batch_writer(hg, node_edge_iter, batch_size=30, err_log_file='error_lines.log', proc_step=1000):
    log = open(err_log_file, 'a')
    
    def batch_nodes(hg, nodes, idx):
        if not nodes:
            return
        try:
            hg.graph.vertices.batch(nodes)
        except Exception as err:
            log.write('node idx:%s, err: %s\n'%(idx, err.args[0].decode()))
    def batch_edges(hg, edges, idx):
        if not edges:
            return
        try:
            hg.graph.edges.batch(edges)
        except Exception as err:
            log.write('edge idx:%s, err: %s\n'%(idx, err.args[0].decode()))
            
    batch_size_1 = batch_size-1
    node_batch, edge_batch = [], []
    st = time.time()
    for idx,(nodes, edges) in enumerate(node_edge_iter):
        node_batch.extend(nodes)
        edge_batch.extend(edges)
        if idx % proc_step == 0:
            print(idx, time.time()-st)
        
        if idx % batch_size == batch_size_1:
            batch_nodes(hg, node_batch, idx)
            batch_edges(hg, edge_batch, idx)
            node_batch, edge_batch = [], []
            
    if node_batch:
        batch_nodes(hg, node_batch, idx)
    if edge_batch:
        batch_edges(hg, edge_batch, idx)
