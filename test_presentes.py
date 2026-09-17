import unittest
from presentes import PRESENTES, efeitos_presente


class PresentesTest(unittest.TestCase):
    def test_presentes_conhecidos(self):
        self.assertEqual(efeitos_presente('rosa'), {'felicidade': 10})
        self.assertEqual(efeitos_presente('coracao'), {'felicidade': 15, 'vida': 5})
        self.assertEqual(efeitos_presente('cafe'), {'energia': 10})
        self.assertEqual(efeitos_presente('leao'), {'energia': 20, 'felicidade': 15, 'vida': 10})

    def test_case_insensitive(self):
        self.assertEqual(efeitos_presente('ROSA'), {'felicidade': 10})
        self.assertEqual(efeitos_presente('Coracao'), {'felicidade': 15, 'vida': 5})
        self.assertEqual(efeitos_presente('CAFE'), {'energia': 10})
        self.assertEqual(efeitos_presente('LEAO'), {'energia': 20, 'felicidade': 15, 'vida': 10})

    def test_presente_desconhecido(self):
        self.assertEqual(efeitos_presente('diamante'), {})
        self.assertEqual(efeitos_presente(''), {})
        self.assertEqual(efeitos_presente('   '), {})

    def test_apenas_quatro_presentes_iniciais(self):
        self.assertEqual(set(PRESENTES.keys()), {'rosa', 'coracao', 'cafe', 'leao'})


if __name__ == '__main__':
    unittest.main(verbosity=2)