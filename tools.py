import arxiv

client = arxiv.Client()

def search_arxiv(title: str, papers_count: int):
    search_query = f'all:"{title}"'
    search = arxiv.Search(
        query=search_query,
        max_results=papers_count,
        sort_by=arxiv.SortCriterion.Relevance
    )
    papers = []
    results = client.results(search)
    for result in results:
        paper = {
            'title': result.title,
            'authors': [author.name for author in result.authors],
            'summary': result.summary,
            'published': result.published,
            'url': result.entry_id
        }