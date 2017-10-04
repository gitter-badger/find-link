from wikilink.wiki_link import WikiLink

def main():
	starting_url = '/wiki/Barack_Obama'
	ending_url = '/wiki/Bill_Clinton'
	model = WikiLink(starting_url,ending_url)
	model.search()
	model.print_links()

if __name__ == "__main__":
	main()