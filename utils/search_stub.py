import logging
import asyncio
from meilisearch import Client
import io
import random
import aiohttp
from functools import lru_cache

import requests
import config


logger = logging.getLogger(__name__)

def get_meilisearch_indexes() -> list[str]:
    """ Get meilisearch indexes """
    indexes = []
    limit = 1000  
    offset = 0
    try:
        while True:
            response = requests.get(
                f"{config.CLIENT_URL}/indexes",
                params={"limit": limit, "offset": offset},
                timeout=5
            )
            if response.status_code != 200:
                logger.warning(f"⚠️ MeiliSearch returned status {response.status_code}")
                break
            data = response.json()
            results = data.get("results", [])
            if not results:
                break
            indexes.extend(idx["uid"] for idx in results)
            offset += len(results)

            if len(results) < limit:
                break  

        return indexes

    except Exception as e:
        logger.error(f"❌ Failed to fetch MeiliSearch indexes: {e}")
        return []

# Get indexes from database
INDEXES = get_meilisearch_indexes()

def save_total_count():
    """
    Save total number of documents to file.
    """
    try:
        client = Client(config.CLIENT_URL, timeout=5)
        
        total_documents = 0
        
        for index_name in INDEXES:
            try:
                index = client.index(index_name)
                stats = index.get_stats()
            
                if hasattr(stats, 'numberOfDocuments'):
                    documents_count = stats.numberOfDocuments
                elif hasattr(stats, 'number_of_documents'):
                    documents_count = stats.number_of_documents
                else:
                    documents_count = stats.get('numberOfDocuments', 0) if hasattr(stats, 'get') else 0
                
                total_documents += documents_count
                
            except Exception as e:
                logging.error(f"Error getting stats for {index_name}: {e}")
                
                continue
        
        with open('total.txt', 'w', encoding='utf-8') as f:
            f.write(str(total_documents))
        
        return total_documents
        
    except Exception as e:
        logger.error(f"Error saving total count: {e}")
        return 0

def get_total_count():
    """
    Read total number of documents from file.
    """
    try:
        with open('total.txt', 'r', encoding='utf-8') as f:
            return int(f.read().strip())
    except:
        return 0

def detect_search_type(query: str) -> str:
    """
    Detects search type.
    """
    query = query.strip().lower()

    if '@' in query and '.' in query.split('@')[-1]:
        return 'email'
    if query.startswith('id') and query[2:].isdigit():
        return 'account_id'
    if query.isdigit() and len(query) <= 10:
        return 'account_id'
    digits_only = ''.join(c for c in query if c.isdigit())
    if len(digits_only) >= 7:
        return 'phone'
    if query.startswith('@') or ('_' in query and not query.isdigit()):
        return 'username'
    return 'name'

@lru_cache(maxsize=32)
async def get_filterable_attributes(index_name: str, session: aiohttp.ClientSession, url: str) -> set:
    async with session.get(f"{url}/indexes/{index_name}") as response:
        if response.status == 200:
            data = await response.json()
            return set(data.get('filterableAttributes', []))
        return set()

async def search_database(query: str, search_type: str = None) -> dict:
    """
    Search: fuzzy for names, strict for username, account_id, email, phone
    """
    if not search_type:
        search_type = detect_search_type(query)

    try:
        client = Client(config.CLIENT_URL)
        query_clean = query.strip()
        query_lower = query_clean.lower()
        all_results = []
        query_words = query_lower.split() 

        def process_index(index_name):
            local_hits = []
            try:
                index = client.index(index_name)
                filterable_attrs = index.get_filterable_attributes()
                if search_type == 'name':
                    search_result = index.search(query_lower, {
                        'matchingStrategy': 'all',
                        'limit': 200
                    })
                    hits = search_result.get('hits', [])

    
                else:
                    field_name = search_type

                    if search_type == 'username' and query_lower.startswith('@'):
                        clean_query = query_lower[1:]
                    elif search_type == 'account_id':
                        if query_lower.startswith('id') and query_clean[2:].isdigit():
                            clean_query = query_clean[2:] 
                        else:
                            clean_query = query_clean
                    else:
                        clean_query = query_clean

                    clean_query = str(clean_query)  

    
                    if field_name in filterable_attrs:
                        search_result = index.search(clean_query, {
                            'filter': f'{field_name} = "{clean_query}"',
                            'limit': 100
                        })
                        hits = search_result.get('hits', [])

                    else:
                        search_result = index.search("", {
                            'matchingStrategy': 'all',
                            'limit': 200
                        })
                        hits = []
                        for hit in search_result.get('hits', []):
                            value = hit.get(field_name)
                            if value is None:
                                continue
                            if str(value) == clean_query:
                                hits.append(hit)

                for hit in hits:
                    local_hits.append({
                        'Name': hit.get('full_name'),
                        'Username': hit.get('username'),
                        'Email': hit.get('email'),
                        'Phone': hit.get('phone'),
                        'Account ID': hit.get('account_id'),
                        'Address': hit.get('address'),
                        'Date of Birth': hit.get('DOB'),
                        'Country': hit.get('country'),
                        'Extra Info': hit.get('extra'),
                        'Source': hit.get('source')
                    })

            except Exception as e:
                logger.error(f"Error searching index {index_name}: {e}")

            return local_hits

        tasks = [asyncio.to_thread(process_index, index_name) for index_name in INDEXES]
        partial_results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in partial_results:
            if isinstance(res, Exception):
                logger.error("Error in processing index: {res}")
                continue
            all_results.extend(res)

        if search_type == 'name':
            all_results = [
                r for r in all_results
                if ' '.join(str(r.get('Name', '')).lower().split()) == query_lower or
                   ' '.join(str(r.get('Name', '')).lower().split()) == ' '.join(query_words[::-1])
            ]


        if search_type == 'name':
            all_results.sort(
                key=lambda x: str(x.get('Name', '')).lower() == query_lower,  
                reverse=True
            )
        else:
            clean_query = query_clean
            if search_type == 'username' and query_lower.startswith('@'):
                clean_query = query_lower[1:]
            elif search_type == 'account_id':
                if query_lower.startswith('id') and query_clean[2:].isdigit():
                    clean_query = query_clean[2:]
            clean_query = str(clean_query)

            all_results.sort(
                key=lambda x: any(
                    (str(v).lower() == query_lower if isinstance(v, str) else str(v) == clean_query)
                    for v in x.values() if v is not None
                ),
                reverse=True
            )


        logger.info(f"Search '{query}' ({search_type}) found {len(all_results)} results")

        return {
            'success': True,
            'query': query,
            'search_type': search_type,
            'results_found': bool(all_results),
            'count': len(all_results),
            'data': all_results
        }

    except Exception as e:
        logger.error(f"Meilisearch error: {e}")
        return {
            'success': False,
            'query': query,
            'search_type': search_type,
            'error': str(e),
            'results_found': False,
            'count': 0,
            'data': []
        }


def generate_results_file(results: dict) -> io.BytesIO:
    """
    Generate result report 
    """
    lines = []
    lines.append("🔍 USER SEARCH RESULTS")
    lines.append("=" * 40)
    lines.append(f"\nQuery: {results.get('query', 'N/A')}")
    lines.append(f"Search Type: {results.get('search_type', 'N/A').capitalize()}")
    lines.append(f"Results Found: {results.get('count', 0)}")
    lines.append("\n" + "=" * 60 + "\n")

    if results.get('results_found'):
        for i, item in enumerate(results['data'], 1):
            lines.append(f"Result #{i}")
            lines.append("-" * 30)
            for key, value in item.items():
                if value and value not in ["N/A", "{}", None, ""]:
                    lines.append(f"{key}: {value}")
            lines.append("\n")
    else:
        lines.append("No results found for your query.\n")

    lines.append("=" * 30)
    lines.append("Search completed successfully.\n")

    file = io.BytesIO("\n".join(lines).encode("utf-8"))
    file.name = f"search_results_{results.get('search_type', 'unknown')}.txt"
    file.seek(0)
    return file

async def is_database_online() -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{config.CLIENT_URL}/health', timeout=2) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('status') == 'available'
                return False
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
    
    

