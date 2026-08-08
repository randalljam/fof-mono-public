# Pinecone Querying with Metadata Filters

https://docs.pinecone.io/guides/data/query-data#query-an-index-with-metadata-filters

## Data

### Query Data
After your data is indexed, you can start sending queries to Pinecone.

The query endpoint searches the index using a query vector. It retrieves the IDs of the most similar records in the index, along with their similarity scores. This endpoint can optionally return the result's vector values and metadata, too. You specify the number of vectors to retrieve each time you send a query. Matches are always ordered by similarity from most similar to least similar.

The similarity score for a vector represents its distance to the query vector, calculated according to the distance metric for the index. The significance of the score depends on the similarity metric. For example, for indexes using the euclidean distance metric, scores with lower values are more similar, while for indexes using the dotproduct metric, higher scores are more similar.

Pinecone is eventually consistent, so there can be a slight delay before new or changed records are visible to queries. See Understanding data freshness to learn about data freshness in Pinecone and how to check the freshness of your data.

### Query Limits
| Metric | Limit |
|--------|--------|
| K2 top_k value | 10,000 |
| K2 result size | 4MB |

The query result size is affected by the dimension of the dense vectors and whether or not dense vector values and metadata are included in the result.

If a query fails due to exceeding the 4MB result size limit, choose a lower top_k value, or use include_metadata=False or include_values=False to exclude metadata or values from the result.

### Send a Query
Each query must include a query vector, specified by either a vector or id, and the number of results to return, specified by the top_k parameter. Each query is also limited to a single namespace within an index. To target a namespace, pass the namespace parameter. To query the default namespace, pass "" or omit the namespace parameter.

Depending on your data and your query, you may get fewer than top_k results. This happens when top_k is larger than the number of possible matching vectors for your query.

For optimal performance when querying with top_k over 1000, avoid returning vector data (include_values=True) or metadata (include_metadata=True).

### Query by Vector
To query by dense vector, provide the vector values representing your query embedding and the topK parameter.

The following example sends a query vector with vector values and retrieves three matching vectors:


Python
JavaScript

Java

Go

C#

curl

from pinecone.grpc import PineconeGRPC as Pinecone

pc = Pinecone(api_key="YOUR_API_KEY")

# To get the unique host for an index, 
# see https://docs.pinecone.io/guides/data/target-an-index
index = pc.Index(host="INDEX_HOST")

index.query(
    namespace="example-namespace",
    vector=[0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
    top_k=3,
    include_values=True
)
The response looks like this:


Python

JavaScript

Java

Go

C#

{
    "matches": [
        {
            "id": "C",
            "score": -1.76717265e-07,
            "values": [0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
        },
        {
            "id": "B",
            "score": 0.080000028,
            "values": [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
        },
        {
            "id": "D",
            "score": 0.0800001323,
            "values": [0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4],
        },
    ],
    "namespace": "example-namespace",
    "usage": {"read_units": 5}
}
​
Query by record ID
To query by record ID, provide the unique record ID and the topK parameter.

The following example sends a query vector with an id value and retrieves three matching vectors:


```python
from pinecone.grpc import PineconeGRPC as Pinecone

pc = Pinecone(api_key="YOUR_API_KEY")

# To get the unique host for an index, 
# see https://docs.pinecone.io/guides/data/target-an-index
index = pc.Index(host="INDEX_HOST")

index.query(
    namespace="example-namespace",
    id="B",
    top_k=3,
    include_values=True
)
```

For more information, see Limitations of querying by ID.

​
Query with metadata filters
Metadata filter expressions can be included with queries to limit the search to only vectors matching the filter expression.

For optimal performance, when querying pod-based indexes with top_k over 1000, avoid returning vector data (include_values=True) or metadata (include_metadata=True).
Use the filter parameter to specify the metadata filter expression. For example, to search for a movie in the “documentary” genre:


```python
from pinecone.grpc import PineconeGRPC as Pinecone

pc = Pinecone(api_key="YOUR_API_KEY")

# To get the unique host for an index, 
# see https://docs.pinecone.io/guides/data/target-an-index
index = pc.Index(host="INDEX_HOST")

index.query(
    namespace="example-namespace",
    vector=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
    filter={
        "genre": {"$eq": "documentary"}
    },
    top_k=1,
    include_metadata=True # Include metadata in the response.
)

# Returns:
# {'matches': [{'id': 'B',
#               'metadata': {'genre': 'documentary'},
#               'score': 0.0800000429,
#               'values': []}],
#  'namespace': 'example-namespace'}
```
For more information about filtering with metadata, see Understanding metadata.

​
Query with sparse and dense vectors
When querying an index containing sparse and dense vectors, include a sparse_vector in your query parameters.

Only indexes using the dotproduct metric support querying sparse vectors.

This feature is in public preview.

Examples

The following example shows how to query with a sparse-dense vector.


```python
query_response = index.query(
    namespace="example-namespace",
    top_k=10,
    vector=[0.1, 0.2, 0.3, 0.4],
    sparse_vector={
        'indices': [3],
        'values':  [0.8]
    }
)
```

To learn more, see Querying sparse-dense vectors.

​
### Query across multiple namespaces
Each query is limited to a single namespace. However, the Pinecone Python SDK provides a query_namespaces utility method to run a query in parallel across multiple namespaces in an index and then merge the result sets into a single ranked result set with the top_k most relevant results.

The query_namespaces method accepts most of the same arguments as query with the addition of a required namespaces parameter.

​
### Python SDK without gRPC
When using the Python SDK without gRPC extras, to get good performance, it is important to set values for the pool_threads and connection_pool_maxsize properties on the index client. The pool_threads setting is the number of threads available to execute requests, while connection_pool_maxsize is the number of cached http connections that will be held. Since these tasks are not computationally heavy and are mainly i/o bound, it should be okay to have a high ratio of threads to cpus.

The combined results include the sum of all read unit usage used to perform the underlying queries for each namespace.

```python
from pinecone import Pinecone

pc = Pinecone(api_key="YOUR_API_KEY")
index = pc.Index(
    name="example-index",
    pool_threads=50,             # <-- make sure to set these
    connection_pool_maxsize=50,  # <-- make sure to set these
)

query_vec = [ 0.1, ...] # an embedding vector with same dimension as the index
combined_results = index.query_namespaces(
    vector=query_vec,
    namespaces=['ns1', 'ns2', 'ns3', 'ns4'],
    metric="cosine",
    top_k=10,
    include_values=False,
    include_metadata=True,
    filter={"genre": { "$eq": "comedy" }},
    show_progress=False,
)

for scored_vec in combined_results.matches:
    print(scored_vec)
print(combined_results.usage)
```

### Python SDK with gRPC
When using the Python SDK with gRPC extras, there is no need to set the connection_pool_maxsize because grpc makes efficient use of open connections by default.

```python
from pinecone.grpc import PineconeGRPC

pc = PineconeGRPC(api_key="API_KEHY")
index = pc.Index(
    name="example-index",
    pool_threads=50, # <-- make sure to set this
)

query_vec = [ 0.1, ...] # an embedding vector with same dimension as the index
combined_results = index.query_namespaces(
    vector=query_vec,
    namespaces=['ns1', 'ns2', 'ns3', 'ns4'],
    metric="cosine",
    top_k=10,
    include_values=False,
    include_metadata=True,
    filter={"genre": { "$eq": "comedy" }},
    show_progress=False,
)

for scored_vec in combined_results.matches:
    print(scored_vec)
print(combined_results.usage)
```

### Query with integrated embedding and reranking
To automatically embed queries and rerank results as part of the search process, use integrated inference.

​
### Data freshness
Pinecone is eventually consistent, so there can be a slight delay before new or changed records are visible to queries. You can use the describe_index_stats endpoint to check data freshness.
