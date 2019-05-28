class Node:
    def __init__(self, node_id, label):
        self.__node_id = node_id
        self.__label = label

    def get_node_id(self):
        return self.__node_id

    def get_label(self):
        return self.__label

    def set_node_id(self, node_id):
        self.__node_id = node_id

    def set_label(self, label):
        self.__label = label


class Edge:
    def __init__(self, edge_id, label, node_from, node_to):
        self.__edge_id = edge_id
        self.__label = label
        self.__node_from = node_from
        self.__node_to = node_to

    def get_edge_id(self):
        return self.__edge_id

    def get_label(self):
        return self.__label

    def get_node_from(self):
        return self.__node_from

    def get_node_to(self):
        return self.__node_to

    def set_edge_id(self, edge_id):
        self.__edge_id = edge_id

    def set_label(self, label):
        self.__label = label

    def set_node_from(self, node_from):
        self.__node_from = node_from

    def set_node_to(self, node_to):
        self.__node_to = node_to


class Graph:
    def __init__(self):
        self.__nodes = []
        self.__edges = []
        self.__node_id_counter = -1
        self.__edge_id_counter = -1

    def get_nodes(self):
        return self.__nodes

    def get_edges(self):
        return self.__edges

    def add_node(self, node):
        self.__nodes.append(node)

    def add_edge(self, edge):
        self.__edges.append(edge)

    def remove_node(self, node):
        if node in self.__nodes:
            self.__nodes.remove(node)

    def remove_edge(self, edge):
        if edge in self.__edges:
            self.__edges.remove(edge)

    def nominate_node_id(self):
        self.__node_id_counter += 1
        return self.__node_id_counter

    def nominate_edge_id(self):
        self.__edge_id_counter += 1
        return self.__edge_id_counter

    def graph_to_dict(self):
        nodes_dict_list = []
        edges_dict_list = []

        for node in self.__nodes:
            nodes_dict_list.append(
                {"id": node.get_node_id(),
                 "label": node.get_label()})
        for edge in self.__edges:
            edges_dict_list.append(
                {"id": edge.get_edge_id(),
                 "label": edge.get_label(),
                 "from": edge.get_node_from().get_node_id(),
                 "to": edge.get_node_to().get_node_id()})

        return {"nodes": nodes_dict_list, "edges": edges_dict_list}
