class Person:
  greeting = "hello"

  def __init__(self, name, age):
    self.name = name
    self.age = age
  
  def hello(self):
    print("hello")

person = Person("Joel", 27)
Person.__setattr__(person, "greeting", "bye")
