from abc import abstractmethod

class Observable:
    """
    A class that represents an observable object in the observer pattern.
    It maintains a list of observers and notifies them of any events.
    """
    def __init__(self):
        self._observers = []

    def attach(self,observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self,observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self,event_type: str,*args,**kwargs):
        for observer in self._observers:
            if event_type=="error":
                observer.update_on_error(self,*args,**kwargs)
            elif event_type=="progress":
                observer.update_progress(self,*args,**kwargs)


class Observer:
    """
    Abstract base class for observers in the Observer pattern.

    Observers must implement the `update_on_error` and `update_progress` methods to handle
    errors and update the progress bar, respectively.
    """
    @abstractmethod
    def update_on_error(self,*args,**kwargs):
        pass
    @abstractmethod
    def update_progress(self,*args,**kwargs):
        pass