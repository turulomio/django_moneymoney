
from django.test import tag

from moneymoney import models, functions
@functions.suppress_stdout
def test_print_object(self):
    b=models.Banks()
    b.name="Newbank"
    b.save()
    functions.print_object(b)
    

def test_string_oneline_object(self):
    b=models.Banks()
    b.name="Newbank"
    b.save()
    assert len(functions.string_oneline_object(b))>0

@tag("fast")
def test_have_different_sign(self):
    assert functions.have_different_sign(1, 1)==False
    assert functions.have_different_sign(1, -1)==True
    assert functions.have_different_sign(-1, 1)==True
    assert functions.have_different_sign(-1, -1)==False
    assert functions.have_different_sign(0, 1)==True
    assert functions.have_different_sign(-1, 0)==True
    assert functions.have_different_sign(0, 0)==True        

@tag("fast")
def test_have_same_sign(self):
    assert functions.have_same_sign(1, 1)==True
    assert functions.have_same_sign(1, -1)==False
    assert functions.have_same_sign(-1, 1)==False
    assert functions.have_same_sign(-1, -1)==True
    assert functions.have_same_sign(0, 1)==False
    assert functions.have_same_sign(-1, 0)==False
    assert functions.have_same_sign(0, 0)==False
    assert functions.have_same_sign(0, -1)==False
    with self.assertRaises(TypeError):
        assert functions.have_same_sign(None, 2)==True
        assert functions.have_same_sign(2, None)==True
        assert functions.have_same_sign(None, None)==True

def test_NoZ(self):
    assert functions.NoZ(1)==False
    assert functions.NoZ(0)==True
    assert functions.NoZ(None)==True
    assert functions.NoZ(-1)==False

@tag("fast")
def test_set_sign_of_other_number(self):
    assert functions.set_sign_of_other_number(1, 1)==1
    assert functions.set_sign_of_other_number(1, -1)==1
    assert functions.set_sign_of_other_number(-1, 1)==-1
    assert functions.set_sign_of_other_number(-1, -1)==-1
