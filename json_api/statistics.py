from article_helpers import get_all_articles, get_article_object
from torngithub import json_decode
import collections
import scipy.stats as st
import operator

""" A set of statistical functions for analyzing collections, papers, etc. """


class Brain:
    """ A 3D representation of the peaks of a paper, or collection of papers """

    # TODO: once working, potentially switch to NumPy arrays
    def init_brain_grid(self):
        """ Create a 3-dimensional representation of the brain. """

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
        """ Return a dict representation of the brain grid. """

        # again, the following approach is possible, but costly.
        # if we want to eventually return an actual array, we can do that
        """
        grid_repr = []
        for i in range(0, 200):
            self.grid_repr.append([])
            for j in range(0, 200):
                self.grid_repr[i].append([])
                for k in range(0, 200):
                    self.grid_repr[i][j].append(0)  # initialize to all zeros

        for coord in self.brain_grid:
            try:
                grid_repr[coord[0] + 100][coord[1] +
                                          100][coord[2] + 100] = self.brain_grid[coord]
            except BaseException:
                # a coordinate fell outside of the range {(-100, 99), (-100,
                # 99), (-100, 99)}
                pass

        return self.grid_repr
        """
        # convert to string keys to be JSON serialized
        string_dict = {}
        for k in self.brain_grid:
            string_dict[str(k)] = self.brain_grid[k]
        return string_dict

    def insert_at_location(self, value, x, y, z, width=1):
        """ Inserts "value" at the corresponding location of the brain grid.

        Take a "width" parameter, which specifies the width of the cube of
        coordinates to affect. """

        half_width = (width - 1) // 2

        top_left_x = x - half_width
        top_left_y = y - half_width
        top_left_z = z - half_width

        # start from the top left corner, and insert a "cube" of "value"s
        for i in range(2 * half_width + 1):
            for j in range(2 * half_width + 1):
                for k in range(2 * half_width + 1):
                    self.brain_grid[(i + top_left_x, j +
                                     top_left_y, k + top_left_z)] = value

    def sum(self, other):
        """ Take a Brain, and upsert its entries into this current brain. Merge process is the sum of two entries. """

        other_grid = other.grid()

        for coord in other_grid:
            self.brain_grid[coord] += other_grid[coord]

        self.total_samples += other.total_samples

    def transform_to_z_scores(self, other):
        """ Take another brain, and calculate the z-score of each coordinate in this brain with respect to the other brain. """
        for k in self.brain_grid:
            # z = (p1hat - p2hat) / sqrt(phat * (1 - phat) * (1 / n1 + 1 / n2))
            # : phat = (n1 * p1hat + n2 * p2hat) / (n1 + n2)
            p1hat = self.brain_grid[k] / self.total_samples
            p2hat = other.brain_grid[k] / other.total_samples
            n1 = self.total_samples
            n2 = other.total_samples
            # assumes that (n1 + n2) != 0; will never occur,
            # since the existence of k => self.total_samples >= 1
            phat = (n1 * p1hat + n2 * p2hat) / (n1 + n2)
            self.brain_grid[k] = (p1hat - p2hat) / \
                ((phat * (1 - phat) * (1 / n1 + 1 / n2))**(.5))

    def transform_to_p_values(self):
        """ Tranform a Brain of z-scores to a Brain of p-values. """
        # survivor function
        for k in self.brain_grid:
            self.brain_grid[k] = st.norm.sf(abs(self.brain_grid[k]))

    def benjamini_hochberg(self, threshold):
        """ Use Benjamini–Hochberg to account for multiple comparisons. """
        filtering_threshold = threshold / self.total_samples
        # get the brain_grid sorted by p-value
        sorted_brain_grid_tuples = sorted(
            self.brain_grid.items(),
            key=operator.itemgetter(1))
        # find the greatest i : P(i) <= i * filtering_threshold
        # (this function actually finds the element right after that, and adds all elements before it)
        i = 0
        found_maximum = False
        for j in range(len(sorted_brain_grid_tuples)):
            if sorted_brain_grid_tuples[j][1] > (j + 1) * filtering_threshold:
                i = j
                found_maximum = True
                break

        if not found_maximum:
            i = len(sorted_brain_grid_tuples)

        self.init_brain_grid()  # add in only the results that are significant
        for k in range(i):
            self.brain_grid[sorted_brain_grid_tuples[k]
                            [0]] = sorted_brain_grid_tuples[k][1]


def get_boolean_map_from_article_object(article, width=5):
    """ Return a Brain of 0s and 1s corresponding to if any coordinate exists at that location, in any of the article's experiment tables. """

    brain = Brain()

    try:
        experiments = json_decode(article.experiments)

        for exp in experiments:
            locations = exp["locations"]
            for coord_string in locations:
                coord = coord_string.split(",")
                try:  # assumes that coordinates are well-formed
                    coord_tuple = (int(float(coord[0])), int(
                        float(coord[1])), int(float(coord[2])))
                    brain.insert_at_location(1, *coord_tuple, width=width)
                except BaseException as e:
                    # malformed coordinate
                    print(e)
                    pass
    except BaseException as e:
        # article not valid, or malformed JSON
        print(e)
        pass

    return brain


def get_boolean_map_from_pmid(pmid, width=5):
    """ Gets a boolean map of an article given a PMID. """

    return get_boolean_map_from_article_object(
        next(get_article_object(pmid)), width)


def significance_from_collections(
        pmids,
        other_pmids=None,
        width=5,
        threshold=.001):
    """ Return a grid representing the p-value/effect size
    at each x, y, z coordinate, with the second collection acting as the
    null hypothesis. Default to entire dataset - pmids. """

    brain = Brain()

    # get the binomial distribution sample for pmids
    # print("Generating cumulative Brain of the articles in this collection...")
    for pmid in pmids:
        # get the boolean repr of this PMID, then sum in the aggregate Brain
        brain_to_sum = get_boolean_map_from_pmid(pmid, width)
        brain.sum(brain_to_sum)

    other_brain = Brain()

    if other_pmids is not None:
        # get the sample for other_pmids
        # print("Generating cumulative Brain of the articles in the other collection...")
        for pmid in other_pmids:
            brain_to_sum = get_boolean_map_from_pmid(pmid, width)
            other_brain.sum(brain_to_sum)

    else:
        all_articles = get_all_articles()
        # TODO: can cache this value once we start using this feature, and instead "subtract" the
        # elements of the collection from (a clone of) the all_articles_brain
        # print("Generating cumulative Brain of all articles in the database, minus the collection...")
        article_checker = set(pmids)
        for article in all_articles:
            if article.pmid not in article_checker:
                brain_to_sum = get_boolean_map_from_article_object(
                    article, width)
                other_brain.sum(brain_to_sum)

    # print("Calculating significance...")
    # calculate significance for each location, brain to other brain
    brain.transform_to_z_scores(other_brain)

    # convert to p values
    brain.transform_to_p_values()
    # print("Filtering insignificant values...")
    # filter for significant values, accounting for multiple comparisons with
    # Benjamini–Hochberg
    brain.benjamini_hochberg(threshold)

    return brain.grid()
