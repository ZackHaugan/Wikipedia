import requests
from bs4 import BeautifulSoup
import urllib.parse
import time

class Page:
    def __init__(self, name:str, parent) -> None:
        """Initializes the page object, with the given page name and parent page (if it has one)
        Will attempt to sanitize user input.
         - If name is an empty sring, will generate and choose a random page (on wikipedia)
        
        name (str): the name of the Wikipedia page
        parent (Page object | None): the parent of the page being created (None if this page is 
            root)"""
        if not isinstance(name, str):
            raise TypeError(f"Page name is not of type string ({type(name)})")
        if parent is not None and not isinstance(parent, Page):
            raise TypeError(f"Page parent is not None or type Page ({type(parent)})")
        if name == "":
            name = requests.get("https://en.wikipedia.org/wiki/Special:Random").url
        self.fullLink = self.__cleanLink(name)
        self.name = self.fullLink[30:].replace("_", " ")
        self.parent = parent 
        
    def getParent(self):
        """Return (Page object | None): returns the parent page of the page"""
        return self.parent
    
    def getName(self) -> str:
        """Return (str): returns the name of the page"""
        return self.name

    def getFullLink(self) -> str:
        """Return (str): returns the full link of the page"""
        return self.fullLink

    def __cleanLink(self, link:str) -> str:
        """Attempts to sanitize input from a string and returns a full url.        
        
        link (str): the name provided for sanitizing

        Return (str): returns the full link of the page"""
        # turn all %XX characters to their character representations, then replace spaces with '_'
        link = urllib.parse.unquote(link).replace(" ", "_")

        if not link.startswith("https://en.wikipedia.org/wiki/"):
            link = f"https://en.wikipedia.org/wiki/{link}"
        return link
    
    def __eq__(self, __o: object) -> bool:
        return self.name == __o.name if isinstance(__o, Page) else False

    def __ne__(self, __o: object) -> bool:
        return not(self == __o)
    
    def __hash__(self) -> int:
        return hash(self.name)
    

class Tree:

    def __init__(self, root:Page, isStarting:bool = True) -> None:
        """Initializes the Tree with the given root and whether this tree is a starting tree.
        Additionally sets up all fields.
        
        root (Page object): the root of the tree
        isStarting (bool): true if this is the starting tree (root is the starting page), otherwise 
            false        
        """
        if not isinstance(root, Page):
            raise TypeError(f"Root of tree is not a page ({type(root)})")
        if not isinstance(isStarting, bool):
            raise TypeError(f"Tree isStarting is not a boolean ({type(isStarting)})")
        
        self.root = root
        self.isStarting = isStarting
        self.endpoints = {root}
        self.queue = {root}
        self.queueLevel = 0
        self.levels = [{root}]
        self.session = requests.Session()

    def getRoot(self) -> Page:
        """Return (Page object): returns the root of the tree (start or end page depending on 
            initialization)"""
        return self.root

    def getEndpoints(self) -> set:
        """Return (set {Page object, ...}): returns the endpoints of the tree (deepest level of nodes)"""
        return self.endpoints

    def getQueueLevel(self) -> int:
        """Return (int): returns the level at which the queue is receiving pages from"""
        return self.queueLevel
    
    def explore(self) -> tuple[bool, set, bool]:
        """Searches a page in the tree and updates the data of the tree.

        Return (tuple (
            bool: true if the search is succesful, otherwise false if no pages can be searched 
                (page does not exist)
            set {Page Object, ...}: the set of new children added to the tree
            bool: true if this search was the last search for the level
        ))"""

        # grab a random page from the queue
        searchPage = self.queue.pop()

        # remove the page being searched from the list of endpoints
        self.endpoints.remove(searchPage)

        children = self.getChildren(searchPage)

        if self.queueLevel == len(self.levels) - 1:
            # the queue we're pulling from is the lowest level of the tree and there is a new level to add 
            # (make a new level set)
            self.levels.append(set())
            
        # add children + connections to appropriate spots
        unseenChildren = children.difference(set().union(*self.levels))

        for child in unseenChildren:
            self.levels[-1].add(child)
            self.endpoints.add(child)

        lastInQueue = False

        if len(self.queue) == 0:
            # if queue is empty, that means that all of the pages at that level of the tree have been searched.
            # look at the next lower level of pages in the tree for the new queue
            self.queueLevel += 1

            if len(self.levels[self.queueLevel]) == 0 :
                # somehow, every page on the level above had no children, no path is possible
                return (False, set(), False)

            lastInQueue = True

            self.queue = self.levels[self.queueLevel].copy()
        
        return (True, unseenChildren, lastInQueue)

    def getChildren(self, searchPage:Page) -> set:
        """Searches the page provided and returns a set of the children of that page
        
        searchPage (Page object): the page that should be searched

        Return (set {Page Object, ...}): the set of children
        """
        if not isinstance(searchPage, Page):
            raise TypeError(f"Page being searched is somehow not a page ({type(searchPage)})")
        
        allPages = set()
        
        if self.isStarting:
            # finding all of the links on a page
            page = BeautifulSoup(self.session.get(searchPage.getFullLink()).text, 'lxml')

            pageBody = page.find_all('div', {"id": "mw-content-text"})

            if len(pageBody) == 0:
                # page has no body to search, either an error in parsing or there is actually no page to search
                # either way ignore the page and return no children
                return set()
            
            for p in pageBody[0].find_all('p'):
                for possLink in (l.get('href') for l in p.find_all('a')):
                    fixed = self.__fixLink(possLink)
                    if fixed != None:
                        allPages.add(Page(fixed, searchPage))
        
        else:
            # finding all of the links that go to a page
            reverse_link = f"https://en.wikipedia.org/wiki/Special:WhatLinksHere?target={searchPage.getName().replace(' ', '_')}&namespace=0&hidetrans=1&hideredirs=1&limit=5000"

            page = BeautifulSoup(self.session.get(reverse_link).text, 'lxml')

            pageList = page.find_all('ul', {"id": "mw-whatlinkshere-list"}, limit=1)

            if len(pageList) == 0:
                # page has no list to search, either an error in parsing or there is actually no pages that link to the page
                # either way ignore the page and return no children
                return set()
            
            for possLink in (l.get('href') for l in pageList[0].find_all('a')):
                fixed = self.__fixLink(possLink)
                if fixed != None:
                    allPages.add(Page(fixed, searchPage))
        
        return allPages

    
    def __fixLink(self, link:str) -> str:
        """fixes and verifies the given links. returns the cleaned link if it is valid, None 
        otherwise.
        
        link (str): the link in which to verify and/or fix

        Return (str | None): the cleaned name of the link provided (prepared to be passed into a 
            page object) if it is valid, otherwise None"""
        if link is None or not link.startswith("/wiki/") or ':' in link:
            return None
        link = urllib.parse.unquote(link[6:]).replace(" ", "_")
        
        pos = link.find('#')
        return link if pos == -1 else link[:pos]


    def __str__(self) -> str:
        """Return (string): the string representation of this tree, following the format:
            1 > {# of pages on level 1} > {# of pages on level 2} > ..."""
        return str([len(l) for l in self.levels][::1 if self.isStarting else -1])[1:-1].replace(', ',' > ')


class Game:
    def __init__(self, startPage:str, endPage:str) -> None:
        """Initializes the Game object with the given start and end pages
        
        startPage (Page object): the starting page of the game (source)
        endPage (Page object): the ending page of the game (destination)"""
        if isinstance(startPage, str):
            self.startTree = Tree(Page(startPage, None), True)
        elif isinstance(startPage, Page):
            self.startTree = Tree(startPage, True)
        else:
            raise TypeError(f"Starting page is not a string or page object ({type(startPage)})")
        if isinstance(endPage, str):
            self.endTree = Tree(Page(endPage, None), False)
        elif isinstance(endPage, Page):
            self.endTree = Tree(endPage, False)
        else:
            raise TypeError(f"Ending page is not a string or page object ({type(startPage)})")
        
        self.searchIndex = 0
        self.paths = []

    
    def search(self, count:int = 5, printInfo:bool = True) -> list:
        """Performs a bidirectional, iterative deeping search on the start and end wikipedia pages 
        until the specified number of solutions have been found. Optionally supresses all printing. 
        returns a list of the new paths found.
         - stores any overflow paths for quick retrieval on a second call to this method
        
        count (int): the number of unique paths to find
        printInfo (bool): true (default) if the function should print the paths and search information, 
            otherwise false

        Return (list [Page object, ...]): the list of paths found (represented as lists of 
            Page objects)"""

        newCount = 0
        targetIndex = self.searchIndex + count
        startTime = time.perf_counter()
        if not isinstance(count, int):
            raise TypeError(f"Count to search is not an integer ({type(count)})")
        
        if printInfo:
            print(f"Finding {count} shortest paths from '{self.startTree.getRoot().getName()}' to '{self.endTree.getRoot().getName()}'")

        if len(self.startTree.getEndpoints()) == 0:
            if(printInfo):
                print("No paths possible (starting tree has no more searchable links)")
            return self.paths[self.searchIndex - newCount:self.searchIndex]
        
        if len(self.endTree.getEndpoints()) == 0:
            if(printInfo):
                print("No paths possible (ending tree has no more pages that link to any of the endpoints)")
            return self.paths[self.searchIndex - newCount:self.searchIndex]

        originalStartIndex = self.searchIndex

        for i in range(self.searchIndex, min(targetIndex, len(self.paths))):
            self.searchIndex += 1
            newCount += 1
            if(printInfo):
                print(f"({newCount}) {self.getPathStringFromPath(self.paths[i])}") 
        
        while self.searchIndex < targetIndex:
            queueEmpty = False
            
            # search the tree that was being searched previously, or the tree with the fewest 
            # endpoints (prioritizing the starting tree if lengths are equal)
            if self.startTree.getQueueLevel() == len(self.startTree.levels) - 2 or (self.endTree.getQueueLevel() == len(self.endTree.levels) - 1 and len(self.startTree.getEndpoints()) <= len(self.endTree.getEndpoints())):
                # search starting tree until the level changes
                endpoints = self.endTree.getEndpoints()
                
                while not queueEmpty and self.searchIndex < targetIndex:
                    res = self.startTree.explore()
                    if printInfo:
                        print(f"\r({time.perf_counter() - startTime:.2f}) {self.getStatusString()}", end="")
                    if not res[0]:
                        # there are no more pages to search, either error or no branches left
                        if(printInfo):
                            print("\nNo paths possible (starting tree has no more searchable links)")
                        return self.paths[originalStartIndex:originalStartIndex + count]
                    
                    if len(endpoints.intersection(res[1])) > 0:
                        # at least one path exists
                        for mid in endpoints.intersection(res[1]):
                            newCount += 1

                            # print path string
                            if(printInfo and self.searchIndex < targetIndex):
                                print(f"\r({newCount}) {self.__getPathString(mid)}") 

                            if(self.searchIndex < targetIndex):
                                self.searchIndex += 1
                            
                            # add path to list
                            self.paths.append(self.__getPath(mid))
                    
                    queueEmpty = res[2]

            else:
                # search ending tree until the level changes
                endpoints = self.startTree.getEndpoints()
                
                while not queueEmpty and self.searchIndex < targetIndex:
                    res = self.endTree.explore()
                    if(printInfo):
                        print(f"\r({time.perf_counter() - startTime:.2f}) {self.getStatusString()}", end="")
                    if not res[0]:
                        # there are no more pages to search, either error or no branches left
                        if(printInfo):
                            print("\nNo paths possible (ending tree has no more pages that link to any of the endpoints)")
                        return self.paths[originalStartIndex:originalStartIndex + count]
                    
                    if len(endpoints.intersection(res[1])) > 0:
                        # at least one path exists
                        for mid in endpoints.intersection(res[1]):
                            newCount += 1

                            # print path string
                            if(printInfo and self.searchIndex < targetIndex):
                                print(f"\r({newCount}) {self.__getPathString(mid)}") 

                            if(self.searchIndex < targetIndex):
                                self.searchIndex += 1
                            
                            # add path to list
                            self.paths.append(self.__getPath(mid))
                            
                    
                    queueEmpty = res[2]
        if(printInfo):
            print(f"\r({time.perf_counter() - startTime:.2f}) {self.getStatusString()}")
        return self.paths[originalStartIndex:originalStartIndex + count] 
        

    def getStatusString(self) -> str:
        """Return (str): creates and returns the status string of the game in the following form:
            1 > {# of children of start} > ... > {# of children of end} > 1"""
        return f"{self.startTree} > ... > {self.endTree}"

    def __getPathString(self, mid:Page) -> str:
        """Generates the path string of a page given a page that is found in both trees
        
        mid (Page object): the page that 'bridges' the gap between the two search trees

        Return (str): the string representation of the path that goes through the provided page"""
        out = mid.getName()

        for startEndpoint in self.startTree.getEndpoints():
            if startEndpoint == mid:
                startMid = startEndpoint
            
        for endEndpoint in self.endTree.getEndpoints():
            if endEndpoint == mid:
                endMid = endEndpoint
        
        midStartParent = startMid.getParent()
        while midStartParent is not None:
            out = f"{midStartParent.getName()} > {out}"
            midStartParent = midStartParent.getParent()
        
        midEndParent = endMid.getParent()
        while midEndParent is not None:
            out = f"{out} > {midEndParent.getName()}"
            midEndParent = midEndParent.getParent()
        
        return out
    

    def __getPath(self, mid:Page) -> list:
        """Generates a list representing the path of a given a page that is found in both trees
        
        mid (Page object): the page that 'bridges' the gap between the two search trees

        Return (list [Page object, ...]): the list representation of the path that goes through the provided page"""

        out = [mid]

        for startEndpoint in self.startTree.getEndpoints():
            if startEndpoint == mid:
                startMid = startEndpoint
            
        for endEndpoint in self.endTree.getEndpoints():
            if endEndpoint == mid:
                endMid = endEndpoint
        
        midStartParent = startMid.getParent()
        while midStartParent is not None:
            out.insert(0, midStartParent)
            midStartParent = midStartParent.getParent()
        
        midEndParent = endMid.getParent()
        while midEndParent is not None:
            out.append(midEndParent)
            midEndParent = midEndParent.getParent()
        
        return out
    

    def getPathStringFromPath(self, path:list) -> str:
        """Generates the path string of a Path given a page that is found in both trees
        
        path (list [Page object, ...]): the path to generate the string representation of

        Return (str): the string representation of the path provided"""
        return " > ".join(page.getName() for page in path)









if __name__ == "__main__":
    start = input("Starting Page: ").strip().title()
    end = input("Ending Page: ").strip().title()
    g = Game(start, end)
    g.search(10)
