#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from typing import Any, Dict, List


#-----------------------------------------------------------#
#       Profile
#-----------------------------------------------------------#

class Profile:
    """ A class that contains lighting properties. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, id: str, status: str, lights: List[str], attributes: Dict[str, Any]):
        self._id = id
        self._status = status
        self._lights = lights
        self._attributes = attributes


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def attributes(self) -> Dict[str, Any]:
        """ Returns the attributes. """
        return self._attributes

    @property
    def id(self) -> str:
        """ Returns the id. """
        return self._id

    @property
    def lights(self) -> List[str]:
        """ Returns the list of lights """
        return self._lights

    @property
    def status(self) -> str:
        """ Returns the status. """
        return self._status