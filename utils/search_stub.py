import logging
import asyncio
from meilisearch import Client
import io
import random
import re
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
    if query.startswith('@'):
        return 'username'
    
    if '@' in query and '.' in query.split('@')[-1]:
        return 'email'
    if query.startswith('id') and query[2:].isdigit():
        return 'account_id'
    if query.isdigit() and len(query) <= 10:
        return 'account_id'
    phone_digits = normalize_phone_digits(query)
    if len(phone_digits) >= 7:
        return 'phone'
    if '_' in query and not query.isdigit():
        return 'username'
    
    return 'name'

def normalize_phone_digits(phone: str) -> str:
    return ''.join(c for c in phone if c.isdigit())


@lru_cache(maxsize=32)
async def get_filterable_attributes(index_name: str, session: aiohttp.ClientSession, url: str) -> set:
    async with session.get(f"{url}/indexes/{index_name}") as response:
        if response.status == 200:
            data = await response.json()
            return set(data.get('filterableAttributes', []))
        return set()

async def search_database(query: str, search_type: str = None) -> dict:
    if not search_type:
        search_type = detect_search_type(query)

    if search_type == 'phone':
        query = normalize_phone_digits(query)
    try:
        client = Client(config.CLIENT_URL)
        query_clean = query.strip()
        query_lower = query_clean.lower()
        all_results = []
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
                    clean_query = query_clean
                    if search_type == 'username' and query_lower.startswith('@'):
                        clean_query = query_lower[1:]
                    elif search_type == 'account_id' and query_lower.startswith('id') and query_clean[2:].isdigit():
                        clean_query = query_clean[2:]

                    if field_name in filterable_attrs:
                        search_result = index.search(clean_query, {
                            'filter': f'{field_name} = "{clean_query}"',
                            'limit': 100
                        })
                        hits = search_result.get('hits', [])
                    else:
                        hits = []
                        search_result = index.search("", {
                            'matchingStrategy': 'all',
                            'limit': 200
                        })
                        for hit in search_result.get('hits', []):
                            value = hit.get(field_name)
                            if value is not None and str(value) == clean_query:
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
                logger.error(f"Error in processing index: {res}")
                continue
            all_results.extend(res)
            
        all_results.sort(
            key=lambda x: str(x.get('Name', '')).lower() == query_lower if search_type=='name' else any(
                (str(v).lower() == query_lower if isinstance(v, str) else str(v) == query_clean)
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

async def deep_search(
    initial_query: str,
    search_type: str = None,
    max_depth: int = 5,
    max_queries: int = 5,
    max_per_hit: int = 5,
    concurrency: int = 5
) -> dict:
    """
    Perform a deep search by recursively searching related fields.
    """
    from asyncio import Semaphore, gather

    def make_uid(hit: dict) -> str:
        parts = []
        for k in ("Email", "Phone", "Username"):
            v = hit.get(k)
            if v:
                if k == "Phone":
                    try:
                        v = normalize_phone_digits(v)
                    except Exception:
                        v = str(v).strip()
                parts.append(str(v).strip().lower())
        return "|".join(parts) if parts else str(hit).strip().lower()

    def get_field(hit: dict, *keys):
        for k in keys:
            v = hit.get(k)
            if v not in (None, ""):
                return v
        return None

    if not search_type:
        try:
            search_type = detect_search_type(initial_query)
        except Exception:
            search_type = None

    queue = [(initial_query, search_type, 0)]
    seen_queries = set()
    aggregated = {}
    queries_done = 0
    sem = Semaphore(concurrency)

    async def run_one_search(q_value: str, q_type: str):
        nonlocal queries_done
        if queries_done >= max_queries:
            return None
        async with sem:
            try:
                if q_type == "phone":
                    q_value_norm = normalize_phone_digits(q_value)
                else:
                    q_value_norm = str(q_value).strip()
                resp = await search_database(q_value_norm, search_type=q_type)
            except Exception as e:
                logger.debug(f"[deep_search] search_database error for {q_value} ({q_type}): {e}")
                return None
        queries_done += 1
        return resp

    idx = 0
    while idx < len(queue):
        current_depth = queue[idx][2]
        if current_depth > max_depth:
            break

        batch = []
        while idx < len(queue) and queue[idx][2] == current_depth:
            batch.append(queue[idx])
            idx += 1

        tasks = []
        for q_value, q_type, depth in batch:
            key_seen = (str(q_value).strip().lower(), q_type or "")
            if key_seen in seen_queries:
                continue
            seen_queries.add(key_seen)
            tasks.append(run_one_search(q_value, q_type))

        if not tasks:
            continue

        results = await gather(*tasks, return_exceptions=True)

        for resp in results:
            if isinstance(resp, Exception) or resp is None:
                continue
            if not isinstance(resp, dict) or not resp.get("success"):
                continue
            hits = resp.get("data") or []
            if not isinstance(hits, list):
                continue

            for hit in hits:
                uid = make_uid(hit)
                if uid not in aggregated:
                    new_hit = dict(hit)
                    for f in ("Phone", "Email", "Username"):
                        val = get_field(new_hit, f)
                        if val:
                            new_hit[f] = str(val).strip()
                    aggregated[uid] = new_hit
                else:
                    existing = aggregated[uid]
                    for k in ("Phone", "Email", "Username"):
                        val = get_field(hit, k)
                        if val and not existing.get(k):
                            existing[k] = str(val).strip()
                    for k, v in hit.items():
                        if k not in ("Phone", "Email", "Username") and v and not existing.get(k):
                            existing[k] = v

            if current_depth < max_depth and queries_done < max_queries:
                new_subs = 0
                for hit in hits:
                    for fld in ("Email", "Phone", "Username"):
                        val = get_field(hit, fld)
                        if not val:
                            continue
                        val_str = str(val).strip()
                        typ = fld.lower()
                        seen_key = (val_str.lower(), typ)
                        if seen_key in seen_queries:
                            continue
                        queue.append((val_str, typ, current_depth + 1))
                        new_subs += 1
                        if new_subs >= max_per_hit:
                            break
                    if new_subs >= max_per_hit:
                        break

        if queries_done >= max_queries:
            break

    data_list = list(aggregated.values())
    return {
        "success": True,
        "query": initial_query,
        "search_type": search_type,
        "depth": max_depth,
        "results_found": bool(data_list),
        "count": len(data_list),
        "data": data_list
    }


def generate_results_file(results: dict) -> io.BytesIO:
    """
    Generate result report.txt
    """
    lines = []
    lines.append("🔍 USER SEARCH RESULTS @OsintRatBot")
    lines.append("=" * 50)
    lines.append(f"\n🔎 Query: {results.get('query', 'N/A')}")
    lines.append(f"📄 Search Type: {results.get('search_type', 'N/A').capitalize()}")
    lines.append(f"📊 Results Found: {results.get('count', 0)}")
    lines.append("\n" + "=" * 50 + "\n")

    if results.get('results_found'):
        for i, item in enumerate(results['data'], 1):
            lines.append(f"🧾 Result #{i}")
            lines.append("-" * 50)
            for key, value in item.items():
                if value and value not in ["N/A", "{}", None, ""]:
                    pretty_key = key.replace("_", " ").title()
                    lines.append(f"• {pretty_key}: {value}")

            lines.append("\n")
    else:
        lines.append("❌ No results found for your query.\n")

    lines.append("=" * 50)
    lines.append("✅ Search completed successfully.\n\n\nt.me/OsintRatBot")

    file_content = "\n".join(lines)
    file = io.BytesIO(file_content.encode("utf-8"))
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
    
    

