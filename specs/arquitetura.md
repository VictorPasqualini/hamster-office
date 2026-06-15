Interface web em formato de escritório que exiba agentes de IA para uso cotidiano, mas também usos mais complexos.
Também será um ambiente compartilhado de trabalho onde humanos e agentes de IA atuam juntos em projetos, tarefas e conversas.
1. A interface precisa ser intuitiva e ter um design que não parece IA.
2. Os agente serão representados em bonecos de hamster
3. O escritório será personalizável, me permitindo adicionar móveis.
4. Os hamsters serão customizáveis assim como personagens de um jogo.
5. O escritório será uma espécie de 3D, no estilo Habbo Hotel, para posicionamento dos móveis e permitir que os Hamsters andem pelo local.
6. Colaboradores poderão entrar para se reunir estilo uma sala de chat, onde comunicação por mensagens serão possíveis.

Definições:
    - Workspace
        Representa uma empresa ou equipe.
        Cada workspace possui: usuários, agentes, projetos, documentos, configurações
    - Usuários
        Pessoas reais que participam do workspace.
        Permissões: administrador, gestor, colaborador, visitante.
    - Agentes
        Funcionários virtuais especializados.
        Exemplos: Agente comercial, Agente financeiro, Agente jurídico, Agente analista de dados, Agente desenvolvdor, Agente atendimento
        Capacidades: participar de chats, criar tarefas, consultar documentos, executar ferramentas, produzir relatórios, solicitar aprovação humana
    - Projetos
        Cada projeto possui: Nome, Cliente, Participantes, Agentes associados, Tarefas, Chats, Arquivos
    - Salas de conversa
        Semelhantes ao slack
        tipos: canal público, canal privado, conversa direta, conversa entre humano e agente
        mensagens devem suportar: texto, arquivos, menções, resposta, histórico
    - Gestão de tarefas
        cada tarefa possui: título, descrição, responsável, status, prioridade, prazo
        Os agentes podem: criar tarefas, atualizar tarefas, sugerir tarefas.
    - Base de conhecimento
        armazena: PDFs, contratos, planilhas, procedimentos, documentação
        Os agentes devem consultar essa base através de RAG
    - Sistema de aprovação
        Ações críticas exigem aprovação humana
        Exemplos: envio de email, assinatura de documentos, aprovação financeira, exclusão de dados
    - Requisitos não-funcionais
        Multi-tenant
        Escalável
        Auditável
        Controle de Permissões
        Histórico completo de ações
        Registro de custos por agente
        Registro de consumo por tokens
    - MVP
        Primeira versão deve conter:
            1. Login
            2. Workspace
            3. Projetos
            4. Chats
            5. Upload de documentos
            6. Agentes especializados
            7. Tarefas
            8. Dashboard administrativo
    - IA
        Ollama:
            Responsabilidades:
                Execução de LLM
                Embeddings
                Inferência local
                Gerenciamento de múltiplos modelos
            Modelos iniciais:
                Qwen3 8B
                    Responsável por:
                        Conversação
                        Planejamento
                        Criação de tarefas
                        Análise de documentos
                        Geração de relatórios
            Todos os agentes utilizam inicialmente o mesmo modelo. A especialização ocorre através de:
                Prompt do sistema
                Ferramentas disponíveis
                Permissões
                Memória
                Contexto do projeto
            Memória:
                Curto prazo
                    Histórico de conversas armazenado no PostgreSQL
                Long Prazo
                    Utilizar pgvector para: Busca semântica, RAG, recuperação de documentos, memória dos agentes
            Os agentes devem ser capazes de utilizar ferramentas externas:
                Banco de dados PostgreSQL
                APIs REST
                Sistema de arquivos
                Documentos do workspace
                Email
                Calendário
                Sistema de tarefas