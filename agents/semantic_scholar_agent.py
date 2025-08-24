import requests
import logging

logger = logging.getLogger(__name__)

def cari_paper_semantic_scholar(query: str, max_results: int = 5) -> list:
    """
    Mencari paper di Semantic Scholar menggunakan API publik mereka.
    """
    api_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    params = {
        'query': query,
        'limit': max_results,
        'fields': 'title,authors,url,abstract'
    }

    headers = {
        'User-Agent': 'AcademicTelegramBot/1.0'
    }

    logger.info(f"Semantic Scholar Agent: Mencari dengan kueri '{query}'")

    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()  
        
        data = response.json()
        
        if not data.get('data'):
            logger.warning(f"Semantic Scholar Agent: Tidak ada hasil untuk kueri '{query}'")
            return []

        hasil_format = []
        for paper in data['data']:
            authors_list = [author['name'] for author in paper.get('authors', [])[:3]]
            authors = ', '.join(authors_list)
            if len(paper.get('authors', [])) > 3:
                authors += ", dkk."
            

            abstract = paper.get('abstract', 'Tidak ada abstrak.')
            if abstract and len(abstract) > 150:
                abstract = abstract[:150] + "..."

            paper_info = (
                f"📄 *Judul:* {paper.get('title', 'Tanpa Judul')}\n"
                f"✍️ *Penulis:* {authors}\n"
                f"📖 *Abstrak:* _{abstract}_\n"
                f"🔗 *Link Halaman:* {paper.get('url', '#')}"
            )
            hasil_format.append(paper_info)
            
        return hasil_format

    except requests.exceptions.RequestException as e:
        logger.error(f"Semantic Scholar Agent: Error saat request API - {e}")
        return [f"Gagal menghubungi Semantic Scholar: {e}"]
    except Exception as e:
        logger.error(f"Semantic Scholar Agent: Error tidak terduga - {e}")
        return [f"Terjadi kesalahan pada agen Semantic Scholar: {e}"]