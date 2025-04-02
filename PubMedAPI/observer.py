from abc import abstractmethod


class Observer:
    @abstractmethod
    def update(self,observable,*args,**kwargs):
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

    def notify(self,*args,**kwargs):
        for observer in self._observers:
            observer.update(self,*args,**kwargs)
