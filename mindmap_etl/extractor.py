from collections import defaultdict

def format_type(s, dtype):
    if dtype == 'TEXT':
        return str(s)
    if dtype == 'INT':
        return int(s)
    if dtype == 'FLOAT':
        return float(s)
    return s

def extract_nodes(idx, row, node_extractors, 
                  schema_field_name='label', values_field_name='properties',
                  format_type_func=None, extract_func=None):
    if format_type_func is None:
        format_type_func = format_type
        
    def extract(row, mapping, schema):
        nodes = {}
        for to,attr in mapping.items():
            if (attr['from'] is None or row.get(attr['from'].name, None) is None):
                if schema['fields'][to].nullable: # 跳过可为空的字段
                    continue
                else:
                    print('Error row: Field no found from %s to %s at line %s'%(attr['from'].name, to, idx))
                    continue
            nodes[to] = format_type_func(row[attr['from'].name], schema['fields'][to]['dtype'])
        return nodes
    extract_func = extract_func or extract
    nodes = defaultdict(dict)
    for i in node_extractors:
        f = node_extractors[i].get('condition', None)
        if f is None or (callable(f) and f(row)):
            nodes[i][values_field_name] = extract_func(row, node_extractors[i]['fields'], node_extractors[i].schema)
            nodes[i][schema_field_name] = node_extractors[i].schema.name
    return dict(nodes)

def extract_edges(idx, row, nodes, edge_extractors,
                  schema_field_name='label', 
                  in_label_field_name='inVLabel',
                  out_label_field_name='outVLabel',
                  in_pk_field_name='inV',
                  out_pk_field_name='outV',
                  values_field_name='properties',
                  format_id_func=None, extract_func=None):

    def format_id(schema, pk):
        return pk

    if format_id_func is None:
        format_id_func = format_id

    def extract(nodes, from_, to_, schema):
        edge = {}
        edge[out_label_field_name] = from_.schema.name
        edge[in_label_field_name] = to_.schema.name
        edge[out_pk_field_name] = format_id_func(
            from_.schema,
            nodes[from_.name][values_field_name][from_.schema.pk]
        )
        edge[in_pk_field_name] = format_id_func(
            to_.schema,
            nodes[to_.name][values_field_name][to_.schema.pk]
        )
        return edge

    extract_func = extract_func or extract

    edges = defaultdict(dict)
    for i, e in edge_extractors.items():
        f = edge_extractors[i].get('condition', None)
        if f is None or (callable(f) and f(row)):
            # edges[i][values_field_name] = extract(row, edge_extractors[i]['fields_mapping']) # TODO
            if e['from'].name in nodes and e['to'].name in nodes:
                edges[i].update(extract_func(nodes, e['from'], e['to'], e.schema))
                edges[i][schema_field_name] = e.schema.name

    return dict(edges)