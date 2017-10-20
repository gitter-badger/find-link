from sqlalchemy import Column, Integer, String, DateTime, text, ForeignKey, func,create_engine
from sqlalchemy.ext.declarative import declarative_base
import re
from requests import get, HTTPError
from bs4 import BeautifulSoup
from sqlalchemy.orm import sessionmaker


Base = declarative_base() #metadata
class Link(Base):
    __tablename__ = 'links'

    id = Column(Integer, primary_key=True)
    from_page_id = Column(Integer, ForeignKey('Page.id'))
    to_page_id = Column(Integer, ForeignKey('Page.id'))
    number_of_separation = Column(Integer,nullable=False)
    created = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    def __repr__(self):
        return "<Link(from_page_id='%s', to_page_id='%s', number_of_separation='%s', created='%s')>" % (
                     self.from_page_id, self.to_page_id, self.number_of_separation, self.created)

class Page(Base):
    __tablename__ = 'pages'

    id = Column(Integer(), primary_key=True)
    url = Column(String(225))
    created = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    def __repr__(self):
        return "<Page(url ='%s', created='%s')>" %(self.url, self.created)

engine = create_engine('mysql://root:12345@192.168.99.100:32771', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
existed_url = set()
session = Session() # having conversation with database

class DataHandle:
    def __init__(self):
        return

    def retrieve_data(self, ending_url, number_of_separation):
        '''

        :param ending_url:
        :param number_of_separation:
        :return: boolean
        '''

        global existed_url

        # query all the page id where to_page id is the parameter
        # when separation is 0, the ending page retrieve itself
        from_page_id_list = session.query(Link.from_page_id).filter(
                                          Link.number_of_separation == number_of_separation,
                                          Link.to_page_id == ending_url).all()

        for url_id in from_page_id_list:

            # retrieve url from id
            url = session.query(Page.url).filter(Page.id == url_id).all()

            # handle exception where page not found or server down or url mistyped
            try:
                html = get('https://en.wikipedia.org' + url[0])
            except HTTPError:
                return
            else:
                if html is None:
                    return
                else:
                    soup = BeautifulSoup(html)

            # update all wiki links with tag 'a' and attribute 'href' start with '/wiki/'
            for link in soup.findAll("a", href=re.compile("^(/wiki/)[^:#]")):

                # only insert link starting with /wiki/ and update Page if not exist
                inserted_url = link.attrs['href']
                self.update_page_if_not_exists(inserted_url)

                # update links table
                inserted_id = session.query(Page.id).filter(Page.url == inserted_url).first()
                self.update_link(int(url_id[0]), int(inserted_id[0]), 1)

                if inserted_url is ending_url:
                    return True
        return False

    def update_page_if_not_exists(self, url):
        ''' insert into table Page if not exist

        :param url:
        :return: null
        '''

        page_list = session.query(Page).filter(Page.url == url).all()
        if page_list.len() == 0:
            existed_url.add(url)
            page = Page(url=url)
            session.add(page)
            session.commit()

    def update_link(self, from_page_id, to_page_id, no_of_separation):
        ''' insert into table Link if link has not existed

        :param from_page_id:
        :param to_page_id:
        :param no_of_separation:
        :return: null
        '''

        link_between_2_pages = session.query(Link).filter(Link.from_page_id == from_page_id,
                                                          Link.to_page_id == to_page_id).all()
        if link_between_2_pages.len() == 0:
            link = Link(from_page_id=Link.from_page_id,
                        to_page_id=to_page_id,
                        number_of_separation = no_of_separation)
            session.add(link)
            session.commit()


class Searcher:
    def __init__(self, starting_page, ending_page):
        self.starting_page = starting_page
        self.ending_page = ending_page
        self.my_list = []

    def link_search(self, current_page, starting_page):
        '''
        :param current_page:
        :param starting_page:
        :return:
        '''
        while starting_page not in self.my_list:
            # retrieve entry in Page with current url
            current_url_id = session.query(Page.id).filter(Page.url == current_page).first()

            # retrieve the the shortest path to the current url using id
            min_separation = session.query(func.min(Link.number_of_separation)).filter(Link.to_page_id == current_url_id[0])

            # retrieve all the id of pages which has min no of separation to current url
            from_page_id = session.query(Link.from_page_id).filter(Link.to_page_id == current_url_id[0], Link.
                                                                   number_of_separation == min_separation)

            #
            url = session.query(Page.url).filter(Page.id == from_page_id[0]).first()
            if url[0] not in self.my_list:
                self.my_list.append(url[0])

            self.link_search(url[0],starting_page)

    def list_of_links(self):
        self.link_search(self.ending_page,self.starting_page)
        return self.my_list


class WikiLink:
    def __init__(self, starting_url, ending_url, limit = 6):
        self.limit = limit
        self.starting_url = starting_url
        self.ending_url = ending_url
        self.found = False
        self.number_of_separation = 0

        self.data_handle = DataHandle()
        self.search = Searcher(self.starting_url, self.ending_url)

        # update page for both starting and ending url
        self.data_handle.update_page_if_not_exists(starting_url)
        self.data_handle.update_page_if_not_exists(ending_url)

        # update link for starting_page, no of separation between 1 url to itself is zero of course
        starting_id = session.query(Page.id).filter(Page.url == starting_url).all()
        self.data_handle.update_link(starting_id[0], starting_id[0], 0)

    def search(self):
        '''

        :return:
        '''

        while self.found is False:
            self.found = self.data_handle.retrieve_data(self.ending_url, self.number_of_separation)
            if self.number_of_separation > self.limit:
                print ("Number of separation is exceeded number of limit...Stop searching!")
                return
            elif self.found is False:
                self.number_of_separation += 1

        print ("Smallest number of separation is " + str(self.number_of_separation))

    def print_links(self):
        """
        print out the sequence of link
        """

        if self.number_of_separation > self.limit or self.found is False:
            print ("No solution within limit! Consider to raise the limit.")
            return

        my_list = [self.ending_url] + self.search.list_of_links()
        my_list.reverse()

        for x in my_list:
            print(x)


