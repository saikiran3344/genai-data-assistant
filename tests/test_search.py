from vectorstore.store import similarity_search

print('=== Query 1: book with highest service transactions ===')
results = similarity_search('which books have highest service transactions', k=3)
for i, doc in enumerate(results, 1):
    print(f'Result {i} (score: {doc.metadata["similarity_score"]}):')
    print(f'  {doc.page_content}')

print()
print('=== Query 2: location of highest public service hours ===')
results = similarity_search('library with highest public service hours', k=3)
for i, doc in enumerate(results, 1):
    print(f'Result {i} (score: {doc.metadata["similarity_score"]}):')
    print(f'  {doc.page_content}')

print()
print('=== Query 3: oldest books ===')
results = similarity_search('oldest books in the state library', k=3)
for i, doc in enumerate(results, 1):
    print(f'Result {i} (score: {doc.metadata["similarity_score"]}):')
    print(f'  {doc.page_content}')