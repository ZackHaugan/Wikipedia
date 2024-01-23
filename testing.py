from main import *
import requests


def validatePath(path) -> bool:
    """Validates a path by using a one-way request from the src to dest (simulating playing the 
    Game)
    
    path (list [Page object, ...]): the path to validate

    Return (bool): true if the path is valid"""

    if (len(path) < 2):
        return False

    # create starting tree
    t = Tree(path[0], True)

    # ensure that the each page is a proper child of the page before it
    for depth in range(0, len(path) - 1):
        if path[depth + 1] not in t.getChildren(path[depth]):
            # if not, then its not a valid path
            return False
    
    return True

def testLength2():

    print("Running testLength2 Test")

    g = Game("United States", "North America")
    res = g.search(1, False)
    assert len(res) == 1
    assert len(res[0]) == 2
    assert validatePath(res[0])
    print(f"testLength2: Passed")

def testLength3():

    print("Running testLength3 Test")

    g = Game("United States", "Donald Trump")
    allLength3Paths = []

    validPaths = 0
    more = True
    while more:
        path = g.search(1, False)
        assert len(path) == 1
        if len(path[0]) == 3:
            allLength3Paths += path[0]
            validPaths += 1 if validatePath(path[0]) else 0
        elif len(path[0]) > 3:
            break

    print(f"testLength3: {validPaths/len(allLength3Paths) * 100:.2f}% paths of length 3 are valid")

    


if __name__ == "__main__":
    testLength2()
    testLength3()

