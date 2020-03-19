class StudyAlreadyExistsException(Exception):
    """
    Exception if the study folder already exists
    """
    pass


class StudyCsvMissingException(Exception):
    """
    Exception if there is no csv file which contains enrolled subjects information
    """
    pass
