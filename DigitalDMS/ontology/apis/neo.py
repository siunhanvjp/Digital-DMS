import json
from neo4j import GraphDatabase
import google.generativeai as genai
import numpy as np
from numpy.linalg import norm
with open("../json/law_synset_vn_backup.json", encoding="utf8") as json_file:
    vietLawSynset = json.load(json_file)
with open("../json/law_rela.json", encoding="utf8") as json_file_rela:
    lawRela = json.load(json_file_rela)
    
# model = genai.GenerativeModel("text-embedding-004")

# print(vietLawSynset[0])


def getTest():
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
            ontology_list = []
            for rec in response.records:
                # pprint.pprint(rec.data())
                # print("----------------------------------------")
                ontology_list.append(rec.data())
            return ontology_list
        except Exception as e:
            print("error in get_all_ontologies: ", e)

def createEmbedding():
    newEmbeddingList = []
    for idx, syn in enumerate(vietLawSynset):
        print(f"\rSynset: {idx} / {len(vietLawSynset)}", end="", flush=True)
        newStr = f"{', '.join(syn['senses'])}: {syn["Definition"]}"
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=newStr,
            task_type="SEMANTIC_SIMILARITY"
            # title="Embedding of single string"
        )
        newObj = syn
        newObj["embedding"] = response["embedding"]
        newEmbeddingList.append(newObj)
        with open("../json/law_synset_vn_test.json", 'w', encoding='utf-8') as json_file:
            json.dump(newEmbeddingList, json_file, ensure_ascii=False, indent=4)

def createFromFile():
    newVietLawSynset = []
    for syn in vietLawSynset:
        newObj = syn
        newObj["label"] = "; ".join(syn["senses"])
        newVietLawSynset.append(newObj)
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        for idx, syn in enumerate(newVietLawSynset):
            print(f"\rSynset: {idx} / {len(newVietLawSynset)}", end="", flush=True)
            try:
                driver.execute_query(
                    """ MERGE (x:Law {name: $label, id: $id})
                        """,
                    label=syn["label"],
                    id=syn["id"],
                    database_="neo4j",
                )
            except Exception as e:
                print("error in upload_ontology", e)
        print("-", end="", flush=True)
        for idx, rela in enumerate(lawRela):
            print(f"\rRela: {idx} / {len(lawRela)}", end="", flush=True)
            try:
                driver.execute_query(
                    """ MATCH (from {id: $from_id})
                        MATCH (to {id: $to_id})
                        MERGE (from)-[r:PARENT_OF {type: $rela_type}]->(to)
                        """,
                    from_id=rela["from"],
                    to_id=rela["to"],
                    rela_type=rela["type"],
                    database_="neo4j",
                )
            except Exception as e:
                print("error in upload_ontology", e)
    # with GraphDatabase.driver(URI, auth=AUTH) as driver:
    #     try:
    #         driver.execute_query(
    #             """ UNWIND $nodelist AS node
    #                 MERGE (x:Law {name: node.label, id: node.id})
    #                 WITH $nodelist AS node
    #                 UNWIND $edgelist AS edge
    #                 MATCH (from {id: edge.from})
    #                 MATCH (to {id: edge.to})
    #                 MERGE (from)-[r:PARENT_OF {type: edge.type}]->(to)
    #                 """,
    #             nodelist=newVietLawSynset,
    #             edgelist=lawRela,
    #             database_="neo4j",
    #         )
    #         return {
    #             "nice": "nice"
    #         }
    #     except Exception as e:
    #         print("error in upload_ontology", e)


def createFromFileNew():
    newVietLawSynset = []
    for syn in vietLawSynset:
        newObj = syn
        newObj["label"] = "; ".join(syn["senses"])
        newVietLawSynset.append(newObj)
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        ontologyResponse = driver.execute_query(
            """
            MERGE (n:Ontology {ontologyName: $name})
            RETURN n
            """,
            name="Full",
            database_="neo4j",
        )
        ontologyId = ontologyResponse.records[0]["n"].element_id
        for idx, syn in enumerate(newVietLawSynset):
            print(f"\rSynset: {idx} / {len(newVietLawSynset)}", end="", flush=True)
            try:
                driver.execute_query(
                    """ MERGE (x:Synset {id: $id, definition: $definition, ontologyId: $ontologyId})
                        WITH x
                        CALL db.create.setNodeVectorProperty(x, 'embedding', apoc.convert.fromJsonList($embedding))
                        """,
                    id=syn["id"],
                    definition=syn["Definition"],
                    ontologyId=ontologyId,
                    embedding=str(syn["embedding"]),
                    database_="neo4j",
                )
                for idx2, sense in enumerate(newVietLawSynset[idx]["senses"]):
                    driver.execute_query(
                        """ MERGE (x:Sense {label: $label, ontologyId: $ontologyId})
                        WITH x
                        MATCH (s:Synset {id: $rid})
                        MERGE (x)-[r:BELONG_TO]->(s)
                        """,
                        label=sense,
                        ontologyId=ontologyId,
                        rid=syn["id"],
                        database_="neo4j",
                    )
            except Exception as e:
                print("error in upload_ontology", e)
        print(f"\r-", end="", flush=True)
        for idx, rela in enumerate(lawRela):
            print(f"\rRela: {idx} / {len(lawRela)}", end="", flush=True)
            try:
                driver.execute_query(
                    """ MATCH (from {id: $from_id})
                        MATCH (to {id: $to_id})
                        MERGE (from)-[r:PARENT_OF {type: $rela_type}]->(to)
                        """,
                    from_id=rela["from"],
                    to_id=rela["to"],
                    rela_type=rela["type"],
                    database_="neo4j",
                )
            except Exception as e:
                print("error in upload_ontology", e)

        driver.execute_query(
            """ CREATE VECTOR INDEX synsetVector IF NOT EXISTS
                FOR (s:Synset)
                ON s.embedding
                OPTIONS {indexConfig: {
                `vector.dimensions`: 768,
                `vector.similarity_function`: 'cosine'
                }}
                """,
            database_="neo4j",
        )
    # with GraphDatabase.driver(URI, auth=AUTH) as driver:
    #     try:
    #         driver.execute_query(
    #             """ UNWIND $nodelist AS node
    #                 MERGE (x:Law {name: node.label, id: node.id})
    #                 WITH $nodelist AS node
    #                 UNWIND $edgelist AS edge
    #                 MATCH (from {id: edge.from})
    #                 MATCH (to {id: edge.to})
    #                 MERGE (from)-[r:PARENT_OF {type: edge.type}]->(to)
    #                 """,
    #             nodelist=newVietLawSynset,
    #             edgelist=lawRela,
    #             database_="neo4j",
    #         )
    #         return {
    #             "nice": "nice"
    #         }
    #     except Exception as e:
    #         print("error in upload_ontology", e)


def get_suggestion():
    original_query = "luật sư"
    queryResponse = genai.embed_content(
        model="models/text-embedding-004",
        content=original_query,
        task_type="SEMANTIC_SIMILARITY"
    )
    
    # OPTIONAL MATCH (parent)-[:PARENT_OF]->(syn)
    # OPTIONAL MATCH (syn)-[:PARENT_OF]->(child)
    # OPTIONAL MATCH (related)-[:BELONG_TO]->(syn)
    # COLLECT(DISTINCT parent) AS resultParent, COLLECT(DISTINCT child) AS resultChild, COLLECT(DISTINCT related) AS resultRelated
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        neoResponse0 = driver.execute_query(
            """
            MATCH (targetList:Sense WHERE 
            toLower($query) CONTAINS ' ' + toLower(targetList.name) + ' ' 
            OR toLower($query) =~ toLower(targetList.name) + ' ' + '.*'
            OR toLower($query) =~ '.*' + ' ' + toLower(targetList.name)
            OR toLower($query) = toLower(targetList.name))
            UNWIND targetList AS target
            CALL{
                WITH target
                MATCH (target)-[r:BELONG_TO]->(syn)
                WITH syn, apoc.convert.fromJsonList($query_embedding) AS queryVector, syn.embedding as synVector
                WITH
                    queryVector,
                    syn,
                    REDUCE(dot = 0, i IN RANGE(0, SIZE(queryVector) - 1) | dot + (queryVector[i] * synVector[i])) AS dotProduct,
                    SQRT(REDUCE(sum = 0, x IN queryVector | sum + x * x)) AS magnitudeA,
                    SQRT(REDUCE(sum = 0, x IN synVector | sum + x * x)) AS magnitudeB
                WITH queryVector, syn, dotProduct / (magnitudeA * magnitudeB) AS similarity
                MATCH (related)-[:BELONG_TO]->(syn)
                WITH queryVector, syn, similarity, related
                OPTIONAL MATCH (parent)-[:PARENT_OF]->(syn)
                WITH queryVector, syn, similarity, related, parent,
                    REDUCE(dot = 0, i IN RANGE(0, SIZE(queryVector) - 1) | dot + (queryVector[i] * parent.embedding[i])) AS parentDotProduct,
                    SQRT(REDUCE(sum = 0, x IN queryVector | sum + x * x)) AS parentMagnitudeA,
                    SQRT(REDUCE(sum = 0, x IN parent.embedding | sum + x * x)) AS parentMagnitudeB
                WITH queryVector, syn, similarity, related, parent, parentDotProduct / (parentMagnitudeA * parentMagnitudeB) AS parentSimilarity
                CALL{
                    WITH parent
                    OPTIONAL MATCH (pNode)-[:BELONG_TO]->(parent)
                    RETURN COLLECT(DISTINCT pNode) AS resultPNode
                }
                WITH queryVector, syn, similarity, related, COLLECT(DISTINCT {parent: parent, resultPNode: resultPNode, similarity: parentSimilarity}) AS resultParent
                OPTIONAL MATCH (syn)-[:PARENT_OF]->(child)
                WITH queryVector, syn, similarity, related, resultParent, child,
                    REDUCE(dot = 0, i IN RANGE(0, SIZE(queryVector) - 1) | dot + (queryVector[i] * child.embedding[i])) AS childDotProduct,
                    SQRT(REDUCE(sum = 0, x IN queryVector | sum + x * x)) AS childMagnitudeA,
                    SQRT(REDUCE(sum = 0, x IN child.embedding | sum + x * x)) AS childMagnitudeB
                WITH syn, similarity, related, resultParent, child, childDotProduct / (childMagnitudeA * childMagnitudeB) AS childSimilarity
                CALL{
                    WITH child
                    OPTIONAL MATCH (cNode)-[:BELONG_TO]->(child)
                    RETURN COLLECT(DISTINCT cNode) AS resultCNode
                }
                WITH syn, similarity, related, resultParent, COLLECT(DISTINCT {child: child, resultCNode: resultCNode, similarity: childSimilarity}) AS resultChild
                RETURN syn, similarity, COLLECT(DISTINCT related) AS resultRelated, apoc.coll.sortMaps(resultParent, 'similarity') AS resultParent, apoc.coll.sortMaps(resultChild, 'similarity') AS resultChild
            }
            WITH target AS resultTarget, COLLECT({syn: syn, similarity: similarity, resultRelated: resultRelated, resultParent: resultParent, resultChild: resultChild}) AS synWithSimilarity
            // Sort synWithSimilarity by similarity in descending order
            WITH resultTarget, apoc.coll.sortMaps(synWithSimilarity, 'similarity') AS sortedSynWithSimilarity
            WITH resultTarget, sortedSynWithSimilarity
            ORDER BY sortedSynWithSimilarity[0].similarity DESC
            RETURN resultTarget, sortedSynWithSimilarity
            """,
            query=original_query,
            query_embedding = str(queryResponse["embedding"]),
            database_="neo4j",
        )
        
        
        # print(neoResponse0.records)
        recList = []
        print("-------------------------------------------------------------")
        for rec in neoResponse0.records:
            # print(rec)
            with open("../json/test.text", 'w', encoding='utf-8') as f:
                f.write(str(rec))
            newObj = {}
            newObj["sense"] = rec["resultTarget"]["name"]
            newObj["neoid"] = rec["resultTarget"].element_id
            newObj["synset"] = [{
                "id": synRec["syn"]["id"],
                "neoid": synRec["syn"].element_id,
                "definition": synRec["syn"]["definition"],
                "cosine": synRec["similarity"],
                "resultRelated": [
                    {
                        "neoid": par.element_id,
                        "name": par["name"]
                    } for par in synRec["resultRelated"]
                ],
                "resultParent": [
                    {
                        "neoid": par['parent'].element_id,
                        "definition": par['parent']["definition"],
                        "similarity": par["similarity"],
                        "senses": [parSense["name"] for parSense in par["resultPNode"]]
                    } for par in synRec["resultParent"] if len(par["resultPNode"]) > 0
                ],
                "resultChild": [
                    {
                        "neoid": chi['child'].element_id,
                        "definition": chi['child']["definition"],
                        "similarity": chi["similarity"],
                        "senses": [chiSense["name"] for chiSense in chi["resultCNode"]]
                    } for chi in synRec["resultChild"] if len(chi["resultCNode"]) > 0 
                ],
            } for synRec in rec["sortedSynWithSimilarity"]]
            recList.append(newObj)
            print("----------------------------------------------------------------------------------------------------------------------------------")
        print(json.dumps(recList, indent=4, ensure_ascii=False))
        # print("suggest", len(neoResponse1.records))
        with open("../json/suggestion_result.json", 'w', encoding='utf-8') as json_file:
            json.dump(recList, json_file, ensure_ascii=False, indent=4)
        
        # # test embedding functions
        # neoResponse2 = driver.execute_query(
        #                 """ MATCH (n WHERE elementId(n)="4:64951cbc-bbdf-4318-9eba-69e89bd47632:398") return n
        #                     """,
        #                     embedding=str(queryResponse["embedding"]),
        #                     database_="neo4j"
        #                     )
        # resultEmbedding = neoResponse2.records[0]["n"]["embedding"]
        # B = np.array(queryResponse["embedding"])
        # A = np.array(resultEmbedding)
        # cosine = np.dot(A,B)/(norm(A)*norm(B))
        # print("Cosine Similarity:", cosine)

# def createIndex():
def createOntology():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        ontologyResponse = driver.execute_query(
            """
            MERGE (n:Ontology {ontologyName: $name})
            RETURN n
            """,
            name="All",
            database_="neo4j",
        )
        print(ontologyResponse.records[0]["n"].element_id)
    
print("-", end='', flush=True)
# print(createFromFileNew())
createFromFileNew()

# get_suggestion()

# createEmbedding()
# createOntology()
