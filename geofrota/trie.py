class No:
    __slots__ = ("rotulo", "filhos", "valores")

    def __init__(self, rotulo=""):
        self.rotulo = rotulo
        # Indexado pelo primeiro caractere do rótulo do filho. Dois filhos nunca
        # começam com o mesmo caractere, senão o prefixo comum já teria virado nó.
        self.filhos = {}
        self.valores = []


def _prefixo_comum(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


class TrieCompacta:
    def __init__(self):
        self.raiz = No()
        self._tamanho = 0

    def __len__(self):
        return self._tamanho

    def inserir(self, chave, valor):
        no = self.raiz
        i = 0
        while i < len(chave):
            filho = no.filhos.get(chave[i])
            if filho is None:
                folha = No(chave[i:])
                folha.valores.append(valor)
                no.filhos[chave[i]] = folha
                self._tamanho += 1
                return
            comum = _prefixo_comum(filho.rotulo, chave[i:])
            if comum < len(filho.rotulo):
                # A chave diverge no meio do rótulo: quebra a aresta em duas.
                meio = No(filho.rotulo[:comum])
                filho.rotulo = filho.rotulo[comum:]
                meio.filhos[filho.rotulo[0]] = filho
                no.filhos[chave[i]] = meio
                filho = meio
            no = filho
            i += comum
        no.valores.append(valor)
        self._tamanho += 1

    def buscar_prefixo(self, prefixo):
        """Todos os valores cujas chaves começam com `prefixo`."""
        no = self.raiz
        i = 0
        while i < len(prefixo):
            filho = no.filhos.get(prefixo[i])
            if filho is None:
                return []
            resto = prefixo[i:]
            if len(resto) <= len(filho.rotulo):
                # O prefixo termina dentro deste rótulo.
                if not filho.rotulo.startswith(resto):
                    return []
                no = filho
                break
            if not resto.startswith(filho.rotulo):
                return []
            no = filho
            i += len(filho.rotulo)
        return self._coletar(no)

    def _coletar(self, no):
        encontrados = []
        pilha = [no]
        while pilha:
            atual = pilha.pop()
            encontrados.extend(atual.valores)
            pilha.extend(atual.filhos.values())
        return encontrados
