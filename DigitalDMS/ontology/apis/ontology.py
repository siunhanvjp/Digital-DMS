from ninja_extra import (
    api_controller,
    http_get,
    http_post,
    http_put,
    http_delete,
    http_patch,
)
from ninja import File
import json
from ninja.files import UploadedFile
from neo4j import GraphDatabase
from router.authenticate import AuthBearer
import unicodedata
import math
import google.generativeai as genai
from ..schema.payload import (
    NewSynsetRequest,
    UpdateNodeNameRequest,
    NewEdgeRequest,
    OntologyGraphRequest,
    NewOntologyRequest,
    RenameOntologyRequest,
    UpdateDefinitionRequest,
    AddSenseRequest,
    AddEdgeRequest,
    UpdateSenseLabel
)
# from underthesea import word_tokenize
from pyvi import ViTokenizer
from openai import OpenAI
import random
URI = ""
AUTH = ("neo4j", "")
# -------------------------------------------utils-----------------------------------
ACCENTS_TABLE = str.maketrans(
    "ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴáàảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ",
    "A" * 17
    + "D"
    + "E" * 11
    + "I" * 5
    + "O" * 17
    + "U" * 11
    + "Y" * 5
    + "a" * 17
    + "d"
    + "e" * 11
    + "i" * 5
    + "o" * 17
    + "u" * 11
    + "y" * 5,
)


def remove_accents(txt: str, type) -> str:
    if not unicodedata.is_normalized("NFC", txt):
        txt = unicodedata.normalize("NFC", txt)
    raw = txt.translate(ACCENTS_TABLE)
    if type == "url":
        return raw.lower().replace(" ", "-")
    else:
        return raw


def transform_options(original_options):
    new_options = []
    for opt in original_options:
        new_opt = {
            "value": opt.element_id,
            "label": opt["name"],
            "compareLabel": remove_accents(opt["name"], "option").lower(),
        }
        new_options.append(new_opt)
    return new_options


def recur_add(parent_node_name, curr_node):
    nodes = []
    edges = []
    new_node = {"label": curr_node["name"]}
    new_edge = {"from": parent_node_name, "to": curr_node["name"]}
    nodes.append(new_node)
    edges.append(new_edge)
    if "children" in curr_node.keys():
        for child in curr_node["children"]:
            result = recur_add(curr_node["name"], child)
            nodes.extend(result["nodes"])
            edges.extend(result["edges"])
    result = {"nodes": nodes, "edges": edges}
    return result


def graph_to_tree(graph):
    # Create a dictionary to store nodes by their id
    node_dict = {node["id"]: {"name": node["label"]} for node in graph["nodes"]}

    # Create a dictionary to store the tree structure
    tree_dict = {}

    for edge in graph["edges"]:
        from_node_id = edge["from"]
        to_node_id = edge["to"]

        # Check if the from_node_id is already in the tree_dict, if not, add it
        if from_node_id not in tree_dict:
            tree_dict[from_node_id] = node_dict[from_node_id]

        # Check if the to_node_id is already in the tree_dict, if not, add it
        if to_node_id not in tree_dict:
            tree_dict[to_node_id] = node_dict[to_node_id]

        # Add the to_node_id as a child of the from_node_id
        if "children" not in tree_dict[from_node_id]:
            tree_dict[from_node_id]["children"] = []
        tree_dict[from_node_id]["children"].append(tree_dict[to_node_id])

    # Find the root node (node with no incoming edges) and return it
    # roots = set(node_dict.keys()) - set(edge["to"] for edge in graph["edges"])
    if graph["ontologyId"] in tree_dict:
        return tree_dict[graph["ontologyId"]]
    else:
        return node_dict[graph["ontologyId"]]





# đây là những thứ cần thêm vào code:
    # from underthesea import word_tokenize
    # from openai import OpenAI
    # from neo4j import GraphDatabase
    # URI = "neo4j+ssc://b147ed11.databases.neo4j.io"
    # AUTH = ("neo4j", "FDga5qQr6g22Th2bhzssL8U_bNRzqeR9Ce-57mo_Zn0")

# dùng ontologyId: "4:6189104e-54a2-4243-81ac-77508424ea24:0"

def get_suggestion_new(ontologyId, original_query):
    # start_time = time.time()
    newQuery = original_query.lower()
    # queryResponse = genai.embed_content(
    #     model="models/text-embedding-004",
    #     content=newQuery,
    #     # task_type="RETRIEVAL_QUERY",
    #     task_type="SEMANTIC_SIMILARITY",
    # )
    responseEmbedding = client.embeddings.create(input=newQuery, model="text-embedding-3-large", dimensions=768).data[0].embedding
    # tokenizeList = word_tokenize(newQuery)
    tokenizeList = [text.replace("_", " ") for text in ViTokenizer.tokenize(newQuery).split(" ")]
    ghepList = [f"{x} {y}" for x, y in zip(tokenizeList, tokenizeList[1:])]
    termlist = tokenizeList + ghepList
    print(termlist)
    # OPTIONAL MATCH (parent)-[:PARENT_OF]->(syn)
    # OPTIONAL MATCH (syn)-[:PARENT_OF]->(child)
    # OPTIONAL MATCH (related)-[:BELONG_TO]->(syn)
    # COLLECT(DISTINCT parent) AS resultParent, COLLECT(DISTINCT child) AS resultChild, COLLECT(DISTINCT related) AS resultRelated
    # print("start")
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        print("start query")
        neoResponse0 = driver.execute_query(
            """
            // CYPHER runtime = parallel
            // PROFILE
            UNWIND $termlist AS term
            CALL{
                WITH term
                MATCH (target:Sense {ontologyId: $ontologyId}) WHERE target.label = term
                WITH target
                MATCH (syn:Synset where ($domainId = "" AND syn.ontologyId = $ontologyId) OR ($domainId <> "" AND syn.domainId=$domainId))<-[r:BELONG_TO]-(target)
                WITH target, COLLECT(DISTINCT syn) AS synList
                UNWIND synList AS syn
                CALL{
                    WITH syn
                    WITH syn, apoc.convert.fromJsonList($query_embedding) AS queryVector, syn.embedding as synVector
                    WITH
                        queryVector,
                        syn,
                        REDUCE(dot = 0, i IN RANGE(0, SIZE(queryVector) - 1) | dot + (queryVector[i] * synVector[i])) AS dotProduct,
                        SQRT(REDUCE(sum = 0, x IN queryVector | sum + x * x)) AS magnitudeA,
                        SQRT(REDUCE(sum = 0, x IN synVector | sum + x * x)) AS magnitudeB
                    
                    WITH queryVector, syn, dotProduct / (magnitudeA * magnitudeB) AS similarity
                    MATCH (related:Sense {ontologyId: $ontologyId})-[:BELONG_TO]->(syn)
                    WITH queryVector, similarity, syn, COLLECT(DISTINCT related) AS relatedList
                    OPTIONAL MATCH (parent:Synset {ontologyId: $ontologyId})-[:PARENT_OF]->(syn)
                    WITH queryVector, similarity, syn, relatedList, COLLECT(DISTINCT parent) AS parentList
                    UNWIND CASE WHEN parentList = [] THEN [null] ELSE parentList END AS parent
                    // UNWIND parentList AS parent
                    CALL{
                        WITH parent, queryVector
                        OPTIONAL MATCH (pNode:Sense {ontologyId: $ontologyId})-[:BELONG_TO]->(parent)
                        WITH parent,
                            COLLECT(DISTINCT pNode) as resultPNode,
                            REDUCE(dot = 0, i IN RANGE(0, SIZE(queryVector) - 1) | dot + (queryVector[i] * parent.embedding[i])) AS parentDotProduct,
                            SQRT(REDUCE(sum = 0, x IN queryVector | sum + x * x)) AS parentMagnitudeA,
                            SQRT(REDUCE(sum = 0, x IN parent.embedding | sum + x * x)) AS parentMagnitudeB
                        WITH resultPNode, parentDotProduct / (parentMagnitudeA * parentMagnitudeB) AS parentSimilarity
                    
                        RETURN resultPNode, parentSimilarity
                    }
                    WITH queryVector, similarity, syn, relatedList, COLLECT({parent: parent, resultPNode: resultPNode, similarity: parentSimilarity}) AS resultParent
                    OPTIONAL MATCH (child:Synset {ontologyId: $ontologyId})<-[:PARENT_OF]-(syn)
                    WITH queryVector, similarity, syn, relatedList, resultParent, COLLECT(DISTINCT child) AS childList
                    UNWIND CASE WHEN childList = [] THEN [null] ELSE childList END AS child
                    // UNWIND childList AS child
                    CALL{
                        WITH child, queryVector
                        OPTIONAL MATCH (cNode:Sense {ontologyId: $ontologyId})-[:BELONG_TO]->(child)
                        WITH child,
                            COLLECT(DISTINCT cNode) as resultCNode,
                            REDUCE(dot = 0, i IN RANGE(0, SIZE(queryVector) - 1) | dot + (queryVector[i] * child.embedding[i])) AS childDotProduct,
                            SQRT(REDUCE(sum = 0, x IN queryVector | sum + x * x)) AS childMagnitudeA,
                            SQRT(REDUCE(sum = 0, x IN child.embedding | sum + x * x)) AS childMagnitudeB
                        WITH resultCNode, childDotProduct / (childMagnitudeA * childMagnitudeB) AS childSimilarity
                    
                        RETURN resultCNode, childSimilarity
                    }
                    WITH similarity, relatedList, resultParent, COLLECT({child: child, resultCNode: resultCNode, similarity: childSimilarity}) AS resultChild
                    RETURN similarity, relatedList, apoc.coll.sortMaps(resultParent, 'similarity') AS resultParent, apoc.coll.sortMaps(resultChild, 'similarity') AS resultChild
                }
                RETURN target AS resultTarget, COLLECT({syn: syn, similarity: similarity, resultRelated: relatedList, resultParent: resultParent, resultChild: resultChild}) AS synWithSimilarity
            }
            WITH resultTarget, synWithSimilarity
            // Sort synWithSimilarity by similarity in descending order
            WITH resultTarget, apoc.coll.sortMaps(synWithSimilarity, 'similarity') AS sortedSynWithSimilarity
            WITH resultTarget, sortedSynWithSimilarity
            ORDER BY sortedSynWithSimilarity[0].similarity DESC
            RETURN resultTarget, sortedSynWithSimilarity
            """,
            termlist = termlist,
            ontologyId=ontologyId if len(ontologyId) != 15 else "4:6189104e-54a2-4243-81ac-77508424ea24:0",
            domainId=ontologyId if len(ontologyId) == 15 else "",
            query_embedding=str(responseEmbedding),
            database_="neo4j",
        )
        # print(neoResponse0.summary.profile['args']['string-representation'])
        print("end query")
        # end_time = time.time()
        # print("time: ", end_time - start_time)
        # print(neoResponse0.records)
        recList = []
        # print("end")
        # print("-------------------------------------------------------------")
        for rec in neoResponse0.records:
            # print(rec)
            newObj = {}
            newObj["sense"] = rec["resultTarget"]["label"]
            newObj["neoid"] = rec["resultTarget"].element_id
            newObj["synset"] = [
                {
                    "id": synRec["syn"]["id"],
                    "neoid": synRec["syn"].element_id,
                    "definition": synRec["syn"]["definition"],
                    "similarity": synRec["similarity"],
                    "resultRelated": [
                        {"neoid": par.element_id, "label": par["label"]}
                        for par in synRec["resultRelated"]
                    ],
                    "resultParent": [
                        {
                            "neoid": par["parent"].element_id,
                            "definition": par["parent"]["definition"],
                            "similarity": par["similarity"],
                            "senses": [
                                parSense["label"] for parSense in par["resultPNode"]
                            ],
                        }
                        for par in synRec["resultParent"]
                        if len(par["resultPNode"]) > 0
                    ],
                    "resultChild": [
                        {
                            "neoid": chi["child"].element_id,
                            "definition": chi["child"]["definition"],
                            "similarity": chi["similarity"],
                            "senses": [
                                chiSense["label"] for chiSense in chi["resultCNode"]
                            ],
                        }
                        for chi in synRec["resultChild"]
                        if len(chi["resultCNode"]) > 0
                    ],
                }
                for synRec in rec["sortedSynWithSimilarity"]
            ]
            recList.append(newObj)
        # print(json.dumps(recList, indent=4, ensure_ascii=False))
        returnObj = {"broader": {}, "related": {}, "narrower": {}, "broaderPoint": {}, "relatedPoint": {}, "narrowerPoint": {}}
        relatedSet = set()
        broaderSet = set()
        narrowerSet = set()
        existSet = set()
        simArray = [rec["synset"][0]["similarity"] for rec in recList]
        # medianThres = stats.median(simArray)
        meanThres = sum(simArray) / len(simArray) if len(simArray) >= 4 else 0
        thresPoint = meanThres
        maxTerm = 20
        # Filter 1: sim threshold
        filterRecList = [rec for rec in recList if rec["synset"][0]["similarity"] >= thresPoint]
        # Filter 2: key in key
        for idx1, rec1 in enumerate(filterRecList):
            if "skip" in rec1 and rec1["skip"] == True:
                continue
            for idx2 in range(idx1+1, len(filterRecList)):
                if "skip" in filterRecList[idx2] and filterRecList[idx2]["skip"] == True:
                    continue
                if rec1["sense"].lower() in filterRecList[idx2]["sense"].lower() or filterRecList[idx2]["sense"].lower() in rec1["sense"].lower():
                    if len(rec1["sense"]) < len (filterRecList[idx2]["sense"]):
                        # print("in if 1", filterRecList[idx1]["sense"])
                        filterRecList[idx1]["skip"] = True
                        filterRecList[idx2]["skip"] = False
                        break
                    else:
                        # print("in if 2", filterRecList[idx1]["sense"])
                        filterRecList[idx1]["skip"] = False
                        filterRecList[idx2]["skip"] = True
            if "skip" not in filterRecList[idx1]:
                # print("in if 3", filterRecList[idx1]["sense"])
                filterRecList[idx1]["skip"] = False
        newRecList = [rec for rec in filterRecList if rec["skip"] == False]
        # newRecList = [rec for rec in filterRecList]
        # Filter 3: get distinct synset
        keyList = set()
        maxEach = math.ceil(maxTerm / (len(newRecList) if len(newRecList) > 0 else 1))
        for rec in newRecList:
            maxRelated = 0
            maxBroader = 0
            maxNarrower = 0
            for chosenSyn in rec["synset"]:
                if chosenSyn["neoid"] not in existSet:
                    for relatedSense in chosenSyn["resultRelated"]:
                        if maxRelated < maxEach and relatedSense["label"] != rec["sense"]:
                            if rec["sense"] not in returnObj["related"]:
                                returnObj["related"][rec["sense"]] = []
                            if relatedSense["label"] not in returnObj["related"][rec["sense"]]:
                                existSet.add(chosenSyn["neoid"])
                                keyList.add(rec["sense"])
                                returnObj["related"][rec["sense"]].append(relatedSense["label"])
                                returnObj["relatedPoint"][chosenSyn["neoid"]] = chosenSyn["similarity"]
                                maxRelated += 1
                        elif maxRelated == maxEach:
                            break
                    for broaderSynset in chosenSyn["resultParent"]:
                        breakOuter = False
                        if broaderSynset["neoid"] not in existSet:
                            for broaderSense in broaderSynset["senses"]:
                                if maxBroader < maxEach and broaderSense != rec["sense"]:
                                    if rec["sense"] not in returnObj["broader"]:
                                        returnObj["broader"][rec["sense"]] = []
                                    if broaderSense not in returnObj["broader"][rec["sense"]]:
                                        keyList.add(rec["sense"])
                                        existSet.add(broaderSynset["neoid"])
                                        returnObj["broader"][rec["sense"]].append(broaderSense)
                                        returnObj["broaderPoint"][broaderSynset["neoid"]] = broaderSynset["similarity"]
                                        maxBroader += 1
                                elif maxBroader == maxEach:
                                    breakOuter = True
                                    break
                        if breakOuter:
                            break
                    for narrowerSynset in chosenSyn["resultChild"]:
                        breakOuter = False
                        if narrowerSynset["neoid"] not in existSet:
                            for narrowerSense in narrowerSynset["senses"]:
                                if maxNarrower < maxEach and narrowerSense != rec["sense"]:
                                    if rec["sense"] not in returnObj["narrower"]:
                                        returnObj["narrower"][rec["sense"]] = []
                                    if narrowerSense not in returnObj["narrower"][rec["sense"]]:
                                        keyList.add(rec["sense"])
                                        existSet.add(narrowerSynset["neoid"])
                                        returnObj["narrower"][rec["sense"]].append(narrowerSense)
                                        returnObj["narrowerPoint"][narrowerSynset["neoid"]] = narrowerSynset["similarity"]
                                        maxNarrower += 1
                                elif maxNarrower == maxEach:
                                    breakOuter = True
                                    break
                        if breakOuter:
                            break
                    break
        returnObj["broaderAvg"] = sum(returnObj["broaderPoint"].values()) / len(returnObj["broaderPoint"].values()) if len(returnObj["broaderPoint"].values()) > 0 else 0
        returnObj["relatedAvg"] = sum(returnObj["relatedPoint"].values()) / len(returnObj["relatedPoint"].values()) if len(returnObj["relatedPoint"].values()) > 0 else 0
        returnObj["narrowerAvg"] = sum(returnObj["narrowerPoint"].values()) / len(returnObj["narrowerPoint"].values()) if len(returnObj["narrowerPoint"].values()) > 0 else 0
        returnObj["pointAvg"] = (returnObj["broaderAvg"] + returnObj["relatedAvg"] + returnObj["narrowerAvg"]) / 3
        print(keyList)
        print("---------")
        
        # Filter 4: key in value
        for key in returnObj["broader"]:
            # print("key", key)
            setToDelete = set()
            for value in returnObj["broader"][key]:
                for eachKey in keyList:
                    if eachKey in value and eachKey != key:
                        # print("eachKey", eachKey)
                        # print("value", value)
                        # print("returnObj['broader'][key]", returnObj["broader"][key])
                        setToDelete.add(value)
            returnObj["broader"][key] = [x for x in returnObj["broader"][key] if x not in setToDelete]
        returnObj["broader"] = {key: value for key, value in returnObj["broader"].items() if len(value) > 0}
        for key in returnObj["related"]:
            setToDelete = set()
            for value in returnObj["related"][key]:
                for eachKey in keyList:
                    if eachKey in value and eachKey != key:
                        # returnObj["related"][key].remove(value)
                        setToDelete.add(value)
            returnObj["related"][key] = [x for x in returnObj["related"][key] if x not in setToDelete]
        returnObj["related"] = {key: value for key, value in returnObj["related"].items() if len(value) > 0}
        for key in returnObj["narrower"]:
            setToDelete = set()
            for value in returnObj["narrower"][key]:
                for eachKey in keyList:
                    if eachKey in value and eachKey != key:
                        # returnObj["narrower"][key].remove(value)
                        setToDelete.add(value)
            returnObj["narrower"][key] = [x for x in returnObj["narrower"][key] if x not in setToDelete]
        returnObj["narrower"] = {key: value for key, value in returnObj["narrower"].items() if len(value) > 0}

        # with open("../json/suggestion_result.json", "w", encoding="utf-8") as json_file:
        #     json.dump(recList, json_file, ensure_ascii=False, indent=4)
        
        # with open("../json/suggestion_format.json", "w", encoding="utf-8") as json_file_format:
        #     json.dump(returnObj, json_file_format, ensure_ascii=False, indent=4)

        # print("suggest", len(neoResponse1.records))
        # # test embedding functions
        # neoResponse2 = driver.execute_query(
        #                 """ MATCH (n WHERE elementId(n)="4:0e19a6b0-5cd5-4af8-bd46-eda617cc5215:17398") return n
        #                     """,
        #                     embedding=str(queryResponse["embedding"]),
        #                     database_="neo4j"
        #                     )
        # resultEmbedding = neoResponse2.records[0]["n"]["embedding"]
        # B = np.array(queryResponse["embedding"])
        # A = np.array(resultEmbedding)
        # similarity = np.dot(A,B)/(norm(A)*norm(B))
        # print("similarity Similarity:", similarity)
        # print("cosine sk", cosine_similarity([queryResponse["embedding"]],[neoResponse2.records[0]["n"]["embedding"]]))
        # print("stop")
        return returnObj



# hàm cũ, ko dùng nữa
def get_suggestion(ontologyId, original_query):
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        try:
            response = driver.execute_query(
                """MATCH (targetList:Node WHERE targetList.ontologyId=$ontologyId AND toLower($query) CONTAINS toLower(targetList.name))
                UNWIND targetList AS target
                CALL{
                    WITH target
                    OPTIONAL MATCH (parent)-->(target)
                    OPTIONAL MATCH  (parent)-->(related WHERE NOT related.name = target.name)
                    OPTIONAL MATCH (target)-->(child)
                    RETURN COLLECT(DISTINCT parent) AS resultParent, COLLECT(DISTINCT target) AS resultTarget, COLLECT(DISTINCT related) AS resultRelated, COLLECT(DISTINCT child) AS resultChild
                }
                RETURN resultTarget, resultParent, resultRelated, resultChild
                """,
                ontologyId=ontologyId,
                query=original_query,
                database_="neo4j",
            )
            result = {}
            for rec in response.records:
                result[rec["resultTarget"][0]["name"]] = {}
                result[rec["resultTarget"][0]["name"]]["broader"] = [
                    node["name"] for node in rec["resultParent"]
                ]
                result[rec["resultTarget"][0]["name"]]["related"] = [
                    node["name"] for node in rec["resultRelated"]
                ]
                result[rec["resultTarget"][0]["name"]]["narrower"] = [
                    node["name"] for node in rec["resultChild"]
                ]
            # json_string = json.dumps(result, indent=4, ensure_ascii=False).encode(
            #     "utf8"
            # )
            # print(json_string.decode())
            output_format = {
                "hình sự": {
                    "broader": ["Pháp luật"],
                    "related": [],
                    "narrower": [
                        "xâm phạm con người",
                        "an ninh quốc gia",
                        "tội phạm quân đội",
                        "tội phạm tư pháp",
                        "tội phạm chức vụ",
                        "xâm phạm hôn nhân và gia đình",
                        "xâm phạm sở hữu",
                        "tội phạm môi trường",
                        "tội phạm ma túy",
                    ],
                },
                "xâm phạm tính mạng": {
                    "broader": ["xâm phạm con người"],
                    "related": [
                        "xâm phạm nhân phẩm danh dự",
                        "xâm phạm quyền tự do",
                        "xâm phạm sức khỏe",
                    ],
                    "narrower": [
                        "giết người",
                        "vượt quá giới hạn phòng vệ",
                        "vứt bỏ con",
                        "vô ý làm chết người",
                        "bức tử",
                        "xúi giục tự sát",
                        "đe dọa giết người",
                    ],
                },
            }
            return result
        except Exception as e:
            print("error in get_suggestion: ", e)


# ---------------------------------------------apis--------------------------------------


@api_controller(prefix_or_class="ontology", tags=["Ontology"])
class OntologyController:
    @http_get("/all")
    def get_all_ontologies(self):
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (ontolist:Root)
                    UNWIND ontolist AS onto
                    CALL{
                        WITH onto
                        MATCH (n {ontologyId: elementId(onto)})
                        OPTIONAL MATCH (n)-[r]-(m)
                        RETURN onto.ontologyId AS ontologyId, onto.name AS name, onto.url AS url, count(DISTINCT n) AS count_nodes, count(DISTINCT r) AS count_edges
                    }
                    RETURN ontologyId, name, url, count_nodes, count_edges
                    """,
                    database_="neo4j",
                )
                print("response in old: ", response.records)
                ontology_list = []
                for rec in response.records:
                    # pprint.pprint(rec.data())
                    # print("----------------------------------------")
                    ontology_list.append(rec.data())
                print("ontology_list: ", ontology_list)
                return ontology_list
            except Exception as e:
                print("error in get_all_ontologies: ", e)


    @http_get("/one/{ontology_url}")
    def get_ontology(self, ontology_url):
        print("hahahahahahahahaha")
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (root:Root {url: $ontology_url})
                        WITH root.name AS name, root.url AS url, elementId(root) AS ontologyId
                        MATCH (n {ontologyId: ontologyId})
                        OPTIONAL MATCH (n)-[r]-(m)
                        OPTIONAL MATCH (child:Node {ontologyId: ontologyId})
                        WHERE NOT (child)<--()
                        RETURN name, url, ontologyId, COLLECT(DISTINCT n) AS nodes, COLLECT(DISTINCT r) AS relationships, COLLECT(DISTINCT child) AS child""",
                    ontology_url=ontology_url,
                    database_="neo4j",
                )
                # print("result_graph: ", response.records[0]["child"])
                result_graph = {
                    "ontologyId": response.records[0]["ontologyId"],
                    "name": response.records[0]["name"],
                    "url": response.records[0]["url"],
                    "nodes": [],
                    "edges": [],
                    "childrenOptions": transform_options(response.records[0]["child"]),
                    "parentOptions": transform_options(response.records[0]["nodes"]),
                }
                for node in response.records[0]["nodes"]:
                    # print("node is: ", node)
                    node_type = list(node.labels)[0]
                    node_text = node["name"]
                    new_node = {"id": node.element_id, "label": node_text}
                    # new_parent_option = {"value": node.element_id, "label": node_text}
                    if node_type == "Root":
                        new_node["color"] = "cyan"
                    result_graph["nodes"].append(new_node)
                    # result_graph["parentOptions"].append(new_parent_option)

                for relationship in response.records[0]["relationships"]:
                    result_graph["edges"].append(
                        {
                            "id": relationship.element_id,
                            # "label": relationship.type,
                            "from": relationship.start_node.element_id,
                            "to": relationship.end_node.element_id,
                            "from_label": relationship.nodes[0]["name"],
                            "to_label": relationship.nodes[1]["name"],
                        }
                    )
                # pprint.pprint(result_graph)
                # print("nodes len: ", len(result_graph["nodes"]))
                # print("edges len: ", len(result_graph["edges"]))
                return result_graph
            except Exception as e:
                print("error in get_ontology: ", e)

    @http_post("/create/scratch")
    def create_ontology(self, data: NewOntologyRequest):
        name = data.name
        url = remove_accents(name, "url")
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                driver.execute_query(
                    """ MERGE (root:Root {name: $name, url: $url})
                        SET root.ontologyId = elementId(root)
                        """,
                    name=name,
                    url=url,
                    database_="neo4j",
                )
                response = {"url": url}
                return response
            except Exception as e:
                print("error in create_ontology", e)

    @http_post("/create/file")
    def upload_ontology(self, ontology_file: UploadedFile = File(...)):
        data = ontology_file.read()
        ontology_json = json.loads(str(data, encoding="utf-8"))
        nodes = []
        edges = []
        ontology = ontology_json["name"]
        url = remove_accents(ontology_json["name"], "url")
        if "children" in ontology_json.keys():
            for child in ontology_json["children"]:
                result = recur_add(ontology_json["name"], child)
                nodes.extend(result["nodes"])
                edges.extend(result["edges"])
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                driver.execute_query(
                    """ MERGE (root:Root {name: $ontology, url: $url})
                        SET root.ontologyId = elementId(root)
                        WITH elementId(root) AS ontologyId
                        UNWIND $nodelist AS node
                        MERGE (x:Node {name: node.label, ontologyId: ontologyId})
                        WITH ontologyId, $nodelist AS node
                        UNWIND $edgelist AS edge
                        MATCH (from {name: edge.from, ontologyId: ontologyId})
                        MATCH (to {name: edge.to, ontologyId: ontologyId})
                        MERGE (from)-[r:PARENT_OF]->(to)
                        """,
                    nodelist=nodes,
                    edgelist=edges,
                    ontology=ontology,
                    url=url,
                    database_="neo4j",
                )
                response = {"url": url}
                return response
            except Exception as e:
                print("error in upload_ontology", e)

    @http_patch("/renameonto/{ontologyId}")
    def rename_ontology(self, ontologyId, data: RenameOntologyRequest):
        name = data.name
        url = remove_accents(name, "url")
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (n:Root WHERE elementId(n)=$ontologyId)
                    SET n.name = $name, n.url = $url
                    WITH n
                    OPTIONAL MATCH (parent {ontologyId: $ontologyId})
                    OPTIONAL MATCH (child:Node {ontologyId: $ontologyId})
                    WHERE NOT (child)<--()
                    RETURN n, COLLECT(DISTINCT parent) AS parent, COLLECT(DISTINCT child) AS child
                    """,
                    ontologyId=ontologyId,
                    name=name,
                    url=url,
                    database_="neo4j",
                )
                result = {
                    "id": ontologyId,
                    "name": name,
                    "url": url,
                    "childrenOptions": transform_options(response.records[0]["child"]),
                    "parentOptions": transform_options(response.records[0]["parent"]),
                }
                return result
            except Exception as e:
                print("error in rename_ontology: ", e)

    @http_post("/node")
    def add_new_node(self, data: NewSynsetRequest):
        name = data.name
        ontologyId = data.ontologyId
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MERGE (n:Node {name: $name, ontologyId: $ontologyId})
                        WITH n
                        OPTIONAL MATCH (parent {ontologyId: $ontologyId})
                        OPTIONAL MATCH (child:Node {ontologyId: $ontologyId})
                        WHERE NOT (child)<--()
                        RETURN n, COLLECT(DISTINCT parent) AS parent, COLLECT(DISTINCT child) AS child
                    """,
                    ontologyId=ontologyId,
                    name=name,
                    database_="neo4j",
                )
                new_node = {
                    "id": response.records[0]["n"].element_id,
                    "label": response.records[0]["n"]["name"],
                    "childrenOptions": transform_options(response.records[0]["child"]),
                    "parentOptions": transform_options(response.records[0]["parent"]),
                }
                # print("new_node: ", new_node)
                return new_node
                # return here
            except Exception as e:
                print("error in add_node: ", e)

    @http_delete("/node/{node_id}")
    def delete_node(self, node_id):
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (n WHERE elementId(n)=$node_id)
                    WITH n, n.ontologyId AS ontologyId
                    DETACH DELETE n
                    WITH ontologyId
                    OPTIONAL MATCH (parent {ontologyId: ontologyId})
                    OPTIONAL MATCH (child:Node {ontologyId: ontologyId})
                    WHERE NOT (child)<--()
                    RETURN COLLECT(DISTINCT parent) AS parent, COLLECT(DISTINCT child) AS child
                    """,
                    node_id=node_id,
                    database_="neo4j",
                )
                # print("response n: ", response.records[0]["n"])
                # print("----------------------------------------------------------")
                # print("response child: ", response.records[0]["child"])
                # print("----------------------------------------------------------")
                # print("response parent: ", response.records[0]["parent"])
                deleted_node = {
                    "id": node_id,
                    "childrenOptions": transform_options(response.records[0]["child"]),
                    "parentOptions": transform_options(response.records[0]["parent"]),
                }
                return deleted_node
            except Exception as e:
                print("error in delete_node: ", e)

    @http_patch("/node/{node_id}")
    def update_node_name(self, node_id, data: UpdateNodeNameRequest):
        name = data.name
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (n WHERE elementId(n)=$node_id)
                    SET n.name = $name
                    WITH n
                    OPTIONAL MATCH (parent {ontologyId: n.ontologyId})
                    OPTIONAL MATCH (child:Node {ontologyId: n.ontologyId})
                    WHERE NOT (child)<--()
                    RETURN n, COLLECT(DISTINCT parent) AS parent, COLLECT(DISTINCT child) AS child
                    """,
                    node_id=node_id,
                    name=name,
                    database_="neo4j",
                )
                updated_node = {
                    "id": response.records[0]["n"].element_id,
                    "label": response.records[0]["n"]["name"],
                    "childrenOptions": transform_options(response.records[0]["child"]),
                    "parentOptions": transform_options(response.records[0]["parent"]),
                }
                return updated_node
            except Exception as e:
                print("error in update_node_name: ", e)

    @http_post("/edge")
    def add_new_edge(self, data: NewEdgeRequest):
        from_id = data.from_id
        to_id = data.to_id
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (from WHERE elementId(from)=$from_id)
                    MATCH (to WHERE elementId(to)=$to_id)
                    MERGE (from)-[r:PARENT_OF]->(to)
                    WITH r, from, to
                    OPTIONAL MATCH (parent {ontologyId: from.ontologyId})
                    OPTIONAL MATCH (child:Node {ontologyId: from.ontologyId})
                    WHERE NOT (child)<--()
                    RETURN r, from, to, COLLECT(DISTINCT parent) AS parent, COLLECT(DISTINCT child) AS child
                    """,
                    from_id=from_id,
                    to_id=to_id,
                    database_="neo4j",
                )

                new_edge = {
                    "id": response.records[0]["r"].element_id,
                    "from": response.records[0]["r"].start_node.element_id,
                    "to": response.records[0]["r"].end_node.element_id,
                    "from_label": response.records[0]["r"].nodes[0]["name"],
                    "to_label": response.records[0]["r"].nodes[1]["name"],
                    "childrenOptions": transform_options(response.records[0]["child"]),
                    "parentOptions": transform_options(response.records[0]["parent"]),
                }
                return new_edge
            except Exception as e:
                print("error in add_relationship: ", e)

    @http_delete("/edge/{edge_id}")
    def delete_edge(self, edge_id):
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (from)-[r:PARENT_OF WHERE elementId(r)=$edge_id]-(to)
                    DELETE r
                    WITH from.ontologyId AS ontologyId
                    OPTIONAL MATCH (parent {ontologyId: ontologyId})
                    OPTIONAL MATCH (child:Node {ontologyId: ontologyId})
                    WHERE NOT (child)<--()
                    RETURN COLLECT(DISTINCT parent) AS parent, COLLECT(DISTINCT child) AS child
                    """,
                    edge_id=edge_id,
                    database_="neo4j",
                )
                deleted_edge = {
                    "id": edge_id,
                    "childrenOptions": transform_options(response.records[0]["child"]),
                    "parentOptions": transform_options(response.records[0]["parent"]),
                }
                # print("deleted_node: ", deleted_edge)
                return deleted_edge
            except Exception as e:
                print("error in delete_edge", e)

    @http_post("/download")
    def download_ontology(self, ontology_graph: OntologyGraphRequest):
        output_tree = graph_to_tree(ontology_graph.__dict__)
        return output_tree

    # ///////////////////////////////////////////////////////////////////////////
    @http_get("/ontologyid/{ontology_id}")
    def get_ontology_id(self, ontology_id):
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = 1
                if len(ontology_id) == 15:
                    response = driver.execute_query(
                        """MATCH (root:Ontology WHERE root.domainId=$ontology_id)
                            WITH root.ontologyName AS ontologyName
                            MATCH (n:Synset {domainId: $ontology_id})
                            WITH ontologyName, COLLECT(DISTINCT n) AS nodes
                            WITH ontologyName, nodes[..$ontoSize] AS nodes
                            UNWIND nodes AS no
                            CALL{
                                WITH no
                                OPTIONAL MATCH (no)-[r]-(m)
                                WITH no, r
                                OPTIONAL MATCH (sen:Sense)-[b:BELONG_TO]->(no)
                                RETURN r, sen
                            }                            
                            WITH ontologyName, nodes, COLLECT(DISTINCT r) AS relationships, COLLECT (DISTINCT sen) AS nodesense
                            RETURN ontologyName, $ontology_id AS ontologyId, nodes, nodesense, relationships, count(distinct nodesense) AS count_sense, count(distinct nodes) AS count_syn""",
                        ontology_id=ontology_id,
                        ontoSize=random.randint(100, 130),
                        database_="neo4j",
                    )
                    # response = driver.execute_query(
                    #     """MATCH (root:Ontology WHERE root.domainId=$ontology_id)
                    #         WITH root.ontologyName AS ontologyName
                    #         MATCH (n:Synset {domainId: $ontology_id})
                    #         OPTIONAL MATCH (n)-[r]-(m)
                    #         WITH ontologyName, COLLECT(DISTINCT n) AS nodes, COLLECT(DISTINCT r) AS relationships
                    #         WITH ontologyName, nodes[..100] AS nodes, relationships AS relationships
                    #         UNWIND nodes AS no
                    #         CALL{
                    #             WITH no
                    #             OPTIONAL MATCH (sen:Sense)-[b:BELONG_TO]->(no)
                    #             RETURN sen
                    #         }
                    #         WITH ontologyName, nodes, relationships, COLLECT (DISTINCT sen) AS nodesense
                    #         RETURN ontologyName, $ontology_id AS ontologyId, nodes, nodesense, relationships, count(distinct nodesense) AS count_sense, count(distinct nodes) AS count_syn""",
                    #     ontology_id=ontology_id,
                    #     database_="neo4j",
                    # )
                else:
                    response = driver.execute_query(
                        """MATCH (root:Ontology WHERE elementId(root)=$ontology_id)
                            WITH root.ontologyName AS ontologyName, elementId(root) AS ontologyId
                            OPTIONAL MATCH (n:Synset {ontologyId: ontologyId})
                            WITH ontologyName, ontologyId, COLLECT(DISTINCT n) AS nodes
                            WITH ontologyName, ontologyId, nodes[..$ontoSize] AS nodes
                            UNWIND CASE WHEN nodes = [] THEN [null] ELSE nodes END AS no
                            CALL{
                                WITH no, ontologyId
                                OPTIONAL MATCH (no)-[r]-(m)
                                WITH no, r, ontologyId
                                OPTIONAL MATCH (sen:Sense {ontologyId: ontologyId})-[b:BELONG_TO]->(no)
                                RETURN r, sen
                            }
                            WITH ontologyName, ontologyId, nodes, COLLECT(DISTINCT r) AS relationships, COLLECT (DISTINCT sen) AS nodesense
                            RETURN ontologyName, ontologyId, nodes, nodesense, relationships, count(distinct nodesense) AS count_sense, count(distinct nodes) AS count_syn""",
                        ontology_id=ontology_id,
                        ontoSize=random.randint(100, 130),
                        database_="neo4j",
                    )
                    # response = driver.execute_query(
                    #     """MATCH (root:Ontology WHERE elementId(root)=$ontology_id)
                    #         WITH root.ontologyName AS ontologyName, elementId(root) AS ontologyId
                    #         OPTIONAL MATCH (n {ontologyId: ontologyId})
                    #         OPTIONAL MATCH (n)-[r]-(m)
                    #         WITH ontologyName, ontologyId, COLLECT(DISTINCT n) AS nodes, COLLECT(DISTINCT r) AS relationships
                    #         WITH ontologyName, ontologyId, nodes[..100] AS nodes, relationships[..1000] AS relationships
                    #         CALL{
                    #             WITH ontologyName, ontologyId, nodes, relationships
                    #             MATCH (sen:Sense {ontologyId: ontologyId})
                    #             RETURN count(distinct sen) as count_sense
                    #         }
                    #         WITH ontologyName, ontologyId, nodes, relationships, count_sense
                    #         CALL{
                    #             WITH ontologyName, ontologyId, nodes, relationships, count_sense
                    #             MATCH (syn:Synset {ontologyId: ontologyId})
                    #             RETURN count(distinct syn) as count_syn
                    #         }
                    #         RETURN ontologyName, ontologyId, nodes, relationships, count_sense, count_syn""",
                    #     ontology_id=ontology_id,
                    #     database_="neo4j",
                    # )
                # print("result_graph: ", response.records)
                result_graph = {
                    "ontologyId": response.records[0]["ontologyId"],
                    "ontologyName": response.records[0]["ontologyName"],
                    "nodes": [],
                    "edges": [],
                    "count_syn": response.records[0]["count_syn"] if response.records[0]["count_syn"] != 1 else len(response.records[0]["nodes"]),
                    "count_sense": response.records[0]["count_sense"] if response.records[0]["count_sense"] != 1 else len(response.records[0]["nodesense"])
                }
                print("yes")
                if (len(response.records[0]["nodes"]) > 0):
                    for node in response.records[0]["nodes"]:
                        # print("node is: ", node)
                        node_type = list(node.labels)[0]
                        # nodeId = node.element_id
                        new_node = {
                            "id": node.element_id,
                            "value": node.element_id,
                            "type": node_type
                        }
                        # new_parent_option = {"value": node.element_id, "label": node_text}
                        if node_type == "Synset":
                            new_node["color"] = "cyan"
                            new_node["label"] = f"Synset {node.element_id.split(':')[2]}"
                            new_node["compareLabel"] = f"Synset {node.element_id.split(':')[2]}"
                            new_node["definition"] = node["definition"]
                            # new_node["label"] = f"Synset"
                            # new_node["compareLabel"] = f"Synset"
                        else:
                            new_node["label"] = node["label"]
                            new_node["compareLabel"] = remove_accents(node["label"], "option")
                            
                        result_graph["nodes"].append(new_node)
                        # result_graph["parentOptions"].append(new_parent_option)
                    # if len(ontology_id) == 15:
                    for node in response.records[0]["nodesense"]:
                        # print("node is: ", node)
                        node_type = list(node.labels)[0]
                        # nodeId = node.element_id
                        new_node = {
                            "id": node.element_id,
                            "value": node.element_id,
                            "type": node_type
                        }
                        # new_parent_option = {"value": node.element_id, "label": node_text}
                        if node_type == "Synset":
                            new_node["color"] = "cyan"
                            new_node["label"] = f"Synset {node.element_id.split(':')[2]}"
                            new_node["compareLabel"] = f"Synset {node.element_id.split(':')[2]}"
                            new_node["definition"] = node["definition"]
                            # new_node["label"] = f"Synset"
                            # new_node["compareLabel"] = f"Synset"
                        else:
                            new_node["label"] = node["label"]
                            new_node["compareLabel"] = remove_accents(node["label"], "option")
                            
                        result_graph["nodes"].append(new_node)
                        # result_graph["parentOptions"].append(new_parent_option)

                if (len(response.records[0]["relationships"]) > 0):
                    for relationship in response.records[0]["relationships"]:
                        result_graph["edges"].append(
                            {
                                "id": relationship.element_id,
                                # "label": relationship.type,
                                "type": relationship.type,
                                "from": relationship.start_node.element_id,
                                "to": relationship.end_node.element_id,
                                "from_label": relationship.nodes[0]["label"] if relationship.nodes[0]["label"] else f"Synset {relationship.start_node.element_id.split(':')[2]}",
                                "to_label": relationship.nodes[1]["label"] if relationship.nodes[1]["label"] else f"Synset {relationship.end_node.element_id.split(':')[2]}",
                            }
                        )
                # pprint.pprint(result_graph)
                # print("nodes len: ", len(result_graph["nodes"]))
                # print("edges len: ", len(result_graph["edges"]))
                # with open("./result_test.json", 'w', encoding='utf-8') as json_file:
                #     json.dump(result_graph, json_file, ensure_ascii=False, indent=4)
                return result_graph
            except Exception as e:
                print("error in get_ontology: ", e)

    @http_get("/ontologyall")
    def get_all_ontologies_new(self):
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (ontolist:Ontology) WHERE ontolist.domainId IS NULL
                    RETURN elementId(ontolist) AS ontologyId, ontolist.ontologyName AS ontologyName, 0 AS count_syn, 0 AS count_sense, ontolist.available AS available
                    """,
                    database_="neo4j",
                )
                response2 = driver.execute_query(
                    """MATCH (ontolist:Ontology) WHERE ontolist.domainId IS NOT NULL
                    RETURN ontolist.domainId AS ontologyId, ontolist.ontologyName AS ontologyName, 0 AS count_syn, 0 AS count_sense, ontolist.available AS available
                    """,
                    database_="neo4j",
                )
                print("response: ", response.records)
                ontology_list_1 = []
                for rec in response.records:
                    ontology_list_1.append(rec.data())
                ontology_list_2 = []
                for rec in response2.records:
                    ontology_list_2.append(rec.data())
                ontology_list_final = ontology_list_1 + ontology_list_2
                # for rec in response.records:
                #     # pprint.pprint(rec.data())
                #     # print("----------------------------------------")
                #     ontology_list.append(rec.data())
                # print("ontology_list: ", ontology_list_final)
                return ontology_list_final
            except Exception as e:
                print("error in get_all_ontologies: ", e)


    @http_post("/create/new")
    def create_ontology_new(self, data: NewOntologyRequest):
        name = data.name
        ontologyId = data.ontologyId
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                responseNeo = 0
                if len(ontologyId) == 15:
                    responseNeo = driver.execute_query(
                        """ MATCH (root:Ontology {domainId: $domainId})
                            SET root.available = 1
                            RETURN root
                            """,
                        domainId=ontologyId,
                        database_="neo4j",
                    ) 
                else:
                    responseNeo = driver.execute_query(
                        """ MERGE (root:Ontology {ontologyName: $name, available: 1})
                            RETURN root
                            """,
                        name=name,
                        database_="neo4j",
                    )
                # print(responseNeo)
                newOntologyId = responseNeo.records[0]["root"].element_id if len(ontologyId) != 15 else ontologyId
                return {"ontologyId": newOntologyId}
            except Exception as e:
                print("error in create_ontology", e)

    
    @http_post("/addsynset")
    def add_synset(self, data: NewSynsetRequest):
        ontologyId = data.ontologyId
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = 1
                if (len(ontologyId) == 15):
                    print("here 1")
                    print(ontologyId)
                    response = driver.execute_query(
                        """CREATE (n:Synset {definition: "", domainId: $domainId, ontologyId: $ontologyId})
                            RETURN n
                        """,
                        domainId=ontologyId,
                        ontologyId="4:6189104e-54a2-4243-81ac-77508424ea24:0",
                        database_="neo4j",
                    )
                else:
                    print("here 2")
                    print(ontologyId)
                    response = driver.execute_query(
                        """CREATE (n:Synset {definition: "", ontologyId: $ontologyId})
                            RETURN n
                        """,
                        ontologyId=ontologyId,
                        database_="neo4j",
                    )
                new_node = {
                    "id": response.records[0]["n"].element_id,
                    "value": response.records[0]["n"].element_id,
                    "type": list(response.records[0]["n"].labels)[0],
                    # "childrenOptions": transform_options(response.records[0]["child"]),
                    # "parentOptions": transform_options(response.records[0]["parent"]),
                    "color": "cyan",
                    "label": f"Synset {response.records[0]['n'].element_id.split(':')[2]}",
                    "compareLabel": f"Synset {response.records[0]['n'].element_id.split(':')[2]}",
                    "definition" : response.records[0]["n"]["definition"]
                }
                # print("new_node: ", new_node)
                return {
                        "new_node": new_node, 
                        "childrenOptions": [],
                        "parentOptions": []
                    }
                    
                # return here
            except Exception as e:
                print("error in add_node: ", e)


    @http_patch("/synsetdefinition/{synset_id}")
    def update_definition(self, synset_id, data: UpdateDefinitionRequest):
        definition = data.definition
        ontologyId = data.ontologyId
        responseEmbedding = client.embeddings.create(input=definition, model="text-embedding-3-large", dimensions=768).data[0].embedding
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (n:Synset WHERE elementId(n)=$synset_id AND n.ontologyId=$ontologyId)
                    SET n.definition = $definition
                    WITH n
                    CALL db.create.setNodeVectorProperty(n, 'embedding', apoc.convert.fromJsonList($embedding))
                    WITH n
                    RETURN n
                    """,
                    synset_id=synset_id,
                    definition=definition,
                    ontologyId=ontologyId if len(ontologyId) != 15 else "4:6189104e-54a2-4243-81ac-77508424ea24:0",
                    embedding=str(responseEmbedding),
                    database_="neo4j",
                )
                updated_node = {
                    "id": response.records[0]["n"].element_id,
                    "definition" : response.records[0]["n"]["definition"]
                }
                return {
                    "updated_node": updated_node,
                    "childrenOptions": [],
                    "parentOptions": [],
                }
            except Exception as e:
                print("error in update_node_name: ", e)
                

    @http_post("/addsense")
    def add_sense(self, data: AddSenseRequest):
        ontologyId = data.ontologyId
        synsetId = data.synsetId
        label = data.label
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MERGE (n:Sense {label: $label, ontologyId: $ontologyId})
                        WITH n
                        MATCH (s:Synset WHERE elementId(s)=$synsetId AND s.ontologyId=$ontologyId)
                        WITH n,s
                        MERGE (n)-[r:BELONG_TO]->(s)
                        RETURN n,r
                    """,
                    ontologyId=ontologyId if len(ontologyId) != 15 else "4:6189104e-54a2-4243-81ac-77508424ea24:0",
                    synsetId=synsetId,
                    label=label,
                    database_="neo4j",
                )
                new_sense = {
                    "id": response.records[0]["n"].element_id,
                    "value": response.records[0]["n"].element_id,
                    "type": "Sense",
                    "label" : response.records[0]["n"]["label"],
                    "compareLabel": remove_accents(response.records[0]["n"]["label"], "option")
                }
                new_rela = {
                    "id": response.records[0]["r"].element_id,
                    # "label": relationship.type,
                    "type": "BELONG_TO",
                    "from": response.records[0]["r"].start_node.element_id,
                    "to": response.records[0]["r"].end_node.element_id,
                    "from_label": label,
                    "to_label": f"Synset {response.records[0]['r'].end_node.element_id.split(':')[2]}",
                }
                # print("new_node: ", new_node)
                return {
                        "new_sense": new_sense, 
                        "new_rela": new_rela,
                        "childrenOptions": [],
                        "parentOptions": []
                    }
                    
                # return here
            except Exception as e:
                print("error in add_node: ", e)


    @http_post("/addedge")
    def add_new_edge_new(self, data: AddEdgeRequest):
        from_id = data.from_id
        to_id = data.to_id
        ontologyId = data.ontologyId
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (from:Synset WHERE elementId(from)=$from_id AND from.ontologyId=$ontologyId)
                    WITH from
                    MATCH (to:Synset WHERE elementId(to)=$to_id AND from.ontologyId=$ontologyId)
                    MERGE (from)-[r:PARENT_OF]->(to)
                    RETURN r, from, to
                    """,
                    from_id=from_id,
                    to_id=to_id,
                    ontologyId=ontologyId if len(ontologyId) != 15 else "4:6189104e-54a2-4243-81ac-77508424ea24:0",
                    database_="neo4j",
                )

                new_edge = {
                    "id": response.records[0]["r"].element_id,
                    "type": "PARENT_OF",
                    "from": response.records[0]["r"].start_node.element_id,
                    "to": response.records[0]["r"].end_node.element_id,
                    "from_label": f"Synset {response.records[0]['r'].start_node.element_id.split(':')[2]}",
                    "to_label": f"Synset {response.records[0]['r'].end_node.element_id.split(':')[2]}"
                }
                return {
                    "new_edge": new_edge,
                    "childrenOptions": [],
                    "parentOptions": [],
                }
            except Exception as e:
                print("error in add_relationship: ", e)
                
                
    @http_post("/addsynedge")
    def add_syn_edge(self, data: AddEdgeRequest):
        from_id = data.from_id
        to_id = data.to_id
        ontologyId = data.ontologyId
        print("from_id", from_id)
        print("to_id", to_id)
        print("ontologyId", ontologyId)
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (from:Sense WHERE elementId(from)=$from_id AND from.ontologyId=$ontologyId)
                    WITH from
                    MATCH (to:Synset WHERE elementId(to)=$to_id AND from.ontologyId=$ontologyId)
                    WITH from, to
                    MERGE (from)-[r:BELONG_TO]->(to)
                    RETURN from, r
                    """,
                    from_id=from_id,
                    to_id=to_id,
                    ontologyId=ontologyId if len(ontologyId) != 15 else "4:6189104e-54a2-4243-81ac-77508424ea24:0",
                    database_="neo4j",
                )
                # print("new edge", response.records)
                new_edge = {
                    "id": response.records[0]["r"].element_id,
                    "type": "BELONG_TO",
                    "from": response.records[0]["r"].start_node.element_id,
                    "to": response.records[0]["r"].end_node.element_id,
                    "from_label": response.records[0]["from"]["label"],
                    "to_label": f"Synset {response.records[0]['r'].end_node.element_id.split(':')[2]}"
                }
                return {
                    "new_edge": new_edge,
                    "childrenOptions": [],
                    "parentOptions": [],
                }
            except Exception as e:
                print("error in add syn edge: ", e)
                
         
    @http_delete("/deledge/{edge_id}/{ontology_id}")
    def delete_edge_new(self, edge_id, ontology_id):
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (from {ontologyId: $ontologyId})-[r WHERE elementId(r)=$edge_id]-(to {ontologyId: $ontologyId})
                    DELETE r
                    """,
                    edge_id=edge_id,
                    ontologyId=ontology_id if len(ontology_id) != 15 else "4:6189104e-54a2-4243-81ac-77508424ea24:0",
                    database_="neo4j",
                )
                deleted_edge = {
                    "id": edge_id,
                }
                # print("deleted_node: ", deleted_edge)
                return {
                    "deleted_edge": deleted_edge,
                    "childrenOptions": [],
                    "parentOptions": []
                }
            except Exception as e:
                print("error in delete_edge", e)



    @http_patch("/sense/{sense_id}")
    def update_sense_label(self, sense_id, data: UpdateSenseLabel):
        ontologyId = data.ontologyId
        label = data.label
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (n:Sense WHERE n.ontologyId=$ontologyId AND elementId(n)=$sense_id)
                    SET n.label = $label
                    RETURN n
                    """,
                    sense_id=sense_id,
                    label=label,
                    ontologyId=ontologyId if len(ontologyId) != 15 else "4:6189104e-54a2-4243-81ac-77508424ea24:0",
                    database_="neo4j",
                )
                updated_sense = {
                    "id": response.records[0]["n"].element_id,
                    "value": response.records[0]["n"].element_id,
                    "type": "Sense",
                    "label" : response.records[0]["n"]["label"],
                    "compareLabel": remove_accents(response.records[0]["n"]["label"], "option")
                }
                return {
                    "updated_sense": updated_sense,
                    "childrenOptions": [],
                    "parentOptions": [],
                }
            except Exception as e:
                print("error in update_node_name: ", e)


    
    @http_patch("/ontorename/{ontologyId}")
    def rename_ontology(self, ontologyId, data: RenameOntologyRequest):
        ontologyName = data.ontologyName
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                response = driver.execute_query(
                    """MATCH (n:Ontology WHERE elementId(n)=$ontologyId)
                    SET n.ontologyName = $ontologyName
                    RETURN n
                    """,
                    ontologyId=ontologyId,
                    ontologyName=ontologyName,
                    database_="neo4j",
                )
                result = {
                    "ontologyId": ontologyId,
                    "ontologyName": ontologyName,
                    "childrenOptions": [],
                    "parentOptions": [],
                }
                return result
            except Exception as e:
                print("error in rename_ontology: ", e)


    @http_delete("/deleteonto/{ontologyId}")
    def delete_ontology(self, ontologyId):
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            try:
                if len(ontologyId) == 15:
                    # print("delete 1", ontologyId)
                    driver.execute_query(
                        """
                        MATCH (root:Ontology WHERE root.domainId=$domainId) 
                        SET root.available = 0
                        """,
                        domainId=ontologyId,
                        database_="neo4j",
                    )
                else:
                    # print("delete 2", ontologyId)
                    driver.execute_query(
                        """
                        MATCH (root:Ontology WHERE elementId(root)=$ontologyId) 
                        DETACH DELETE root
                        WITH root
                        MATCH (n {ontologyId: $ontologyId})
                        DETACH DELETE n
                        """,
                        ontologyId=ontologyId,
                        database_="neo4j",
                    )
                # print("ontology deleted successfully")
                return {"ontologyId": ontologyId}
            except Exception as e:
                print("error in delete_ontology: ", e)


# get_suggestion_new("4:6189104e-54a2-4243-81ac-77508424ea24:0", "quyền lợi của người lao động tại nơi làm việc")
