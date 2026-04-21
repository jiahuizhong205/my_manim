from manim import *
class Hello(Scene):
    def construct(self):
        hello = Text("Hello Manim!")
        self.play(Write(hello))
        self.wait(2)