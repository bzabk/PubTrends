from abc import abstractmethod


class Observer:
    @abstractmethod
    def update_on_error(self,observable,*args,**kwargs):
        pass
    @abstractmethod
    def update_progress(self,observable,*args,**kwargs):
        pass

class Observable:

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
