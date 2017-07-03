from article_helpers import get_article_object
import collections

""" A set of statistical functions for analyzing collections, papers, etc. """


class Brain:
    """ A 3D representation of the peaks of a paper, or collection of papers """

    # TODO: once working, switch to NumPy arrays
    def init_brain_grid(self):
        """ Create a 3-dimensional 200x200x200 representation of the brain,
        representing {(-100, 99), (-100, 99), (-100, 99)} """

        # because there are far more coordinate locations that there are peaks, the
        # following approach isn't wise
        """
        self.brain_grid = []
        for i in range(0, 200):
            self.brain_grid.append([])
            for j in range(0, 200):
                self.brain_grid[i].append([])
                for k in range(0, 200):
                    self.brain_grid[i][j].append(0) # initialize to all zeros
        """
        # better off using a hash map
        self.brain_grid = collections.defaultdict(lambda: 0)

    def __init__(self):
        self.init_brain_grid()
        # indicating the number of PMIDs that this brain represents
        self.total_samples = 1

    def grid(self):
        """ Return the brain grid. The coordinate system is shifted by (-100, -100, -100). Extremely costly operation. """
        grid_repr = []
        for i in range(0, 200):
            self.grid_repr.append([])
            for j in range(0, 200):
                self.grid_repr[i].append([])
                for k in range(0, 200):
                    self.grid_repr[i][j].append(0)  # initialize to all zeros

        for coord in self.brain_grid:
            grid_repr[coord[0] + 100][coord[1] + \
                100][coord[2] + 100] = self.brain_grid[coord]

        return self.grid_repr

    def insert_at_location(self, value, x, y, z):
        """ Inserts "value" at the corresponding location of the brain grid. """

        self.brain_grid[(x, y, z)] = value

    def sum(self, other):
        """ Take a Brain, and upsert its entries into this current brain. Merge process is the sum of two entries. """

        other_grid = other.grid()

        for coord in other_grid:
            self.grid[coord] += other_grid[coord]

        self.total_samples += other.total_samples


def get_boolean_map_from_pmid(pmid):
    """ Return a Brain of 0s and 1s corresponding to if any coordinate exists at that location, in any of the PMID's experiment tables. """

    brain = Brain()

    # TODO: get the experiments for this PMID, and insert each coordinate into
    # the Brain

    return brain


def significance_from_collections(pmids, other_pmids=None):
    """ Return a Brain representing the p-value/effect size
    at each x, y, z coordinate, with the second collection acting as the
    null hypothesis. Default to entire dataset - pmids. """

    brain = Brain()

    # get the binomial distribution sample for pmids

    for pmid in pmids:
        # get the boolean repr of this PMID, then sum in the aggregate Brain
        brain_to_sum = get_boolean_map_from_pmid(pmid)
        brain.sum(brain_to_sum)

    other_brain = Brain()

    if other_pmids is not None:
        # get the sample for other_pmids
        for pmid in other_pmids:
            brain_to_sum = get_boolean_map_from_pmid(pmid)
            other_brain.sum(brain_to_sum)

    else:
        pass
        # TODO: get the sample for the entire dataset - pmids

    # TODO: calculate significance for each location, brain to other brain

    # TODO: implement BH FDR

    return brain
