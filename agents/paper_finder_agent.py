import arxiv
import logging


logger = logging.getLogger(__name__)

def cari_paper_ilmiah(query: str, max_results: int = 5) -> list:
    """
    Fungsi agen yang bertanggung jawab untuk mencari paper di arXiv.
    Fungsi ini tidak tahu apa-apa tentang Telegram, tugasnya hanya mencari.
    """
    formatted_query = " AND ".join(query.split())
    logger.info(f"Paper Finder Agent: Query asli '{query}', diubah menjadi '{formatted_query}'")
    try:
        
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        hasil_format = []
        results = list(search.results()) 
        
        if not results:
            logger.warning(f"Paper Finder Agent: Tidak ada hasil untuk query '{query}'")
            return ["Maaf, tidak ada paper yang cocok dengan pencarian Anda."]

        for result in results:
            authors = ', '.join(author.name for author in result.authors)
            paper_info = (
                f"📄 *Judul:* {result.title}\n"
                f"✍️ *Penulis:* {authors}\n"
                f"🔗 *Link PDF:* {result.pdf_url}"
            )
            hasil_format.append(paper_info)
        
        return hasil_format

    except Exception as e:
        logger.error(f"Paper Finder Agent: Terjadi error - {e}")
        return [f"Terjadi kesalahan internal saat mencari paper: {e}"]