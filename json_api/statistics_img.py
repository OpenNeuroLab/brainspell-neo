""" A set of statistical functions for analyzing collections, papers, etc. """

# import collections
# import operator

import numpy as np
import scipy.linalg as lin
import scipy.stats as st
from torngithub import json_decode

from article_helpers import get_all_articles, get_article_object

# CONSTANTS
BRAIN3mmSHAPE = (53, 63, 46)
AFF = [[-3., 0., 0.,   78.]
       [0.,  3., 0., -112.]
       [0.,  0., 3.,  -50.]
       [0.,  0., 0.,    1.]]

INVAFF = lin.inv(AFF)


class Brain:
    """ A 3D representation of the peaks of a paper, or collection of papers """

    # TODO: once working, potentially switch to NumPy arrays
    def init_brain_grid(self):
        """ Create a 3-dimensional representation of the brain. """

        # because there are far more coordinate locations that there are peaks,
        # the following approach isn't wise
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
        # self.brain_grid = collections.defaultdict(lambda: 0)

        # create array
        self.brain_grid = np.array(BRAIN3mmSHAPE, dtype=int)

    def __init__(self, total_samples=1):
        # JB: why default to 1 and not 0 ?
        self.init_brain_grid()
        # indicating the number of PMIDs that this brain represents
        self.total_samples = total_samples

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
        """
        string_dict = {}
        for k in self.brain_grid:
            string_dict[str(k)] = self.brain_grid[k]
        return string_dict
        """
        return self.brain_grid

    def coords(self):
        """
        returns the coordinates in the grid that are non zero and non nan
        """

        coords = np.where(np.logical_and(~np.isnan(self.brain_grid),
                                         self.brain_grid > 0))
        self.coords = list(zip(*coords))

    def insert_at_location(self, value, x, y, z):
        """ Insert "value" at the corresponding location of the brain grid.

        Take a "width" parameter, which specifies the width of the cube of
        coordinates to affect. """

        """
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
        """
        # transform coordinate into indices for brain_grid volume
        # Homogeneous coordinates:
        talairach_coo = np.array([x, y, z, 1])
        talairach_coo = talairach_coo.reshape(4, 1)
        # or : talairach_coo = talairach_coo[np.newaxis,:].T
        vox_coo = np.rint(INVAFF.dot(talairach_coo)).astype(int)

        self.brain_grid[tuple(vox_coo[:3])] = 1

    def dilate_grid(self, width=1):
        """
        Apply dilatation on the brain_grid

        Parameters:
        -----------
        width: int
            the radius of the ball to dilute with
        Returns:
        --------
        Self.brain_grid diluted
        """
        import scipy.ndimage.morphology as morph

        # first define how to construct a ball
        def construct_ball(dim=3, radius=1):
            """
            Create a ball in 3 dimension with radius 'radius'
            Diameter will be 2*radius + 1

            parameters
            ----------
            dim: int
                dimension of the space - only 3 is implemented
            radius: int
                radius of the sphere
            """
            try:
                assert(dim == 3)
            except:
                raise NotImplementedError

            # make a cube
            assert radius >= 1, print('radius >= 1')
            radius = np.rint(radius)
            cube_length = int(radius*2 + 1)
            ball = np.zeros((cube_length, cube_length, cube_length))

            # coord contains the range of coordinates
            coord = np.arange(cube_length)
            mesh = np.meshgrid(coord, coord, coord)

            # center the mesh coordinates
            mesh = tuple([mesh[i]-radius for i in range(dim)])

            # keep those less or equal to radius
            ball_coord = np.sqrt(mesh[0]**2 + mesh[1]**2 + mesh[2]**2) <= radius
            ball[np.where(ball_coord)] = 1

            return ball

        ball = construct_ball(dim=3, radius=width)
        self.brain_grid = morph.binary_dilation(self.brain_grid, structure=ball)

    def sum(self, other):
        """ Take a Brain, and upsert its entries into this current brain. Merge
        process is the sum of two entries. """
        """
        other_grid = other.grid()

        for coord in other_grid:
            self.brain_grid[coord] += other_grid[coord]
        """
        assert(self.brain_grid.shape == other.brain_grid.shape)
        self.brain_grid += other.brain_grid
        self.total_samples += other.total_samples

    def transform_to_z_scores(self, other):
        """ Take another brain, and calculate the z-score of each coordinate in
        this brain with respect to the other brain."""
        """
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
        """
        n1 = self.total_samples
        n2 = other.total_samples

        p1hat = self.brain_grid.astype(float)/n1
        p2hat = self.brain_grid.astype(float)/n2

        phat = (n1 * p1hat + n2 * p2hat) / (n1 + n2)
        denominator = (phat * (1 - phat) * (1 / n1 + 1 / n2))**(.5)
        non_zero = denominator != 0
        values = (p1hat(non_zero) - p2hat(non_zero))/denominator(non_zero)
        # put minus infinity for the z-score where it cannot be computed
        # so that p-value is 1 ? or nan ?
        self.brain_grid = np.nan
        self.brain_grid[non_zero] = values

    def transform_to_p_values(self):
        """
        z brain to p brain
        for k in self.brain_grid:
            self.brain_grid[k] = st.norm.sf(abs(self.brain_grid[k]))
        """

        # dont work on non a numeral values
        not_nan = ~np.isnan(self.brain_grid)
        self.brain_grid[not_nan] = st.norm.sf(self.brain_grid[not_nan])

    def benjamini_hochberg(self, threshold):
        """
        Use Benjamini–Hochberg to account for multiple comparisons.  """
        """
        filtering_threshold = threshold / self.total_samples
        # get the brain_grid sorted by p-value
        sorted_brain_grid_tuples = sorted(
            self.brain_grid.items(),
            key=operator.itemgetter(1))
        # find the greatest i : P(i) <= i * filtering_threshold
        # (this function actually finds the element right after that, and adds
        # all elements before it)
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
        """

        from statsmodels.sandbox.stats import multicomp as mc

        # extract p-value
        non_nan = ~np.isnan(self.brain_grid)
        pvals = self.brain_grid(non_nan)
        pvals_coo = np.where(non_nan)

        # return signif a boolean array
        signif, _, _, _ = mc.multipletests(pvals, method='fdr_bh')
        x_ = pvals_coo[0][signif]
        y_ = pvals_coo[1][signif]
        z_ = pvals_coo[2][signif]

        self.init_brain_grid()
        self.brain_grid[x_, y_, z_] = 1


def get_boolean_map_from_article_object(article, width=3):
    """
    Return a Brain of 0s and 1s corresponding to if any coordinate exists at
    that location, in any of the article's experiment tables.
    """

    brain = Brain()

    try:
        experiments = json_decode(article.experiments)

        for exp in experiments:
            locations = exp["locations"]
            for coord_string in locations:
                coord = coord_string.split(",")
                try:  # assumes that coordinates are well-formed
                    coord_tuple = (int(float(coord[0])),
                                   int(float(coord[1])),
                                   int(float(coord[2])))
                    brain.insert_at_location(1, *coord_tuple)
                except BaseException as e:
                    # malformed coordinate
                    print('malformed coordinate', e)
                    pass
        # once all coordinates are inserted, dilute with morphomath
        brain.dilate_grid(width=width)

    except BaseException as e:
        # article not valid, or malformed JSON
        print(e, "failed to put experiments in brain_grid")
        pass

    return brain


def get_boolean_map_from_pmid(pmid, width=5):
    """ Get a boolean map of an article given a PMID. """

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

    brain = Brain(total_samples=0)

    # get the binomial distribution sample for pmids
    # print("Generating cumulative Brain of the articles in this collection...")
    for pmid in pmids:
        # get the boolean repr of this PMID, then sum in the aggregate Brain
        brain_to_sum = get_boolean_map_from_pmid(pmid, width)
        brain.sum(brain_to_sum)

    other_brain = Brain(total_samples=0)

    if other_pmids is not None:
        # get the sample for other_pmids print("Generating cumulative Brain of
        # the articles in the other collection...")
        for pmid in other_pmids:
            brain_to_sum = get_boolean_map_from_pmid(pmid, width)
            other_brain.sum(brain_to_sum)

    else:
        all_articles = get_all_articles()
        # TODO: can cache this value once we start using this feature, and
        # instead "subtract" the elements of the collection from (a clone of)
        # the all_articles_brain print("Generating cumulative Brain of all
        # articles in the database, minus the collection...")
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
