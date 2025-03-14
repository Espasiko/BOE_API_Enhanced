import unittest
from unittest.mock import patch, MagicMock
from your_module import Agent, PlanningAgent, PythonAgent, SummarizationAgent, PythonAgentWorkflow

class TestAgent(unittest.TestCase):

    @patch('your_module.QdrantClient')
    def test_run(self, MockQdrantClient):
        # Configurar el mock
        mock_client = MockQdrantClient()
        mock_client.search.return_value = "mock_response"

        # Crear una instancia del agente
        agent = Agent("test_collection")

        # Ejecutar el método run
        response = agent.run("test_query")

        # Verificar que el método search fue llamado con los argumentos correctos
        mock_client.search.assert_called_once_with(
            collection_name="test_collection",
            query_vector="test_query",
            top=5
        )

        # Verificar la respuesta
        self.assertEqual(response, "mock_response")

    @patch('your_module.QdrantClient')
    def test_run_with_error(self, MockQdrantClient):
        # Configurar el mock para lanzar una excepción
        mock_client = MockQdrantClient()
        mock_client.search.side_effect = Exception("Test exception")

        # Crear una instancia del agente
        agent = Agent("test_collection")

        # Ejecutar el método run
        response = agent.run("test_query")

        # Verificar que la respuesta es None
        self.assertIsNone(response)

class TestPythonAgentWorkflow(unittest.TestCase):

    def setUp(self):
        self.planning_agent = PlanningAgent("ag:977f4f16:20250311:planningagent:ede524f0")
        self.python_agent = PythonAgent("ag:977f4f16:20250311:pythonagent:19b69527")
        self.summarization_agent = SummarizationAgent("ag:977f4f16:20250311:summarizationagent:6aaba406")
        self.workflow = PythonAgentWorkflow(self.planning_agent, self.python_agent, self.summarization_agent)

    @patch('your_module.PlanningAgent.run')
    @patch('your_module.PythonAgent.run')
    @patch('your_module.SummarizationAgent.run')
    def test_workflow(self, MockSummarizationRun, MockPythonRun, MockPlanningRun):
        # Configurar los mocks
        MockPlanningRun.return_value = "## Step 1: Step 1 content\n## Step 2: Step 2 content\n## Total number of steps: 2"
        MockPythonRun.return_value = "```python\nprint('Hello, World!')\n```"
        MockSummarizationRun.return_value = "Summary content"

        # Ejecutar el flujo de trabajo
        planning_result = self.workflow.workflow("test_query")

        # Verificar que los métodos run fueron llamados con los argumentos correctos
        MockPlanningRun.assert_called_once_with("test_query")
        MockPythonRun.assert_called()
        MockSummarizationRun.assert_called_once_with("test_query" + "Hello, World!")

        # Verificar la respuesta
        self.assertEqual(planning_result, "## Step 1: Step 1 content\n## Step 2: Step 2 content\n## Total number of steps: 2")

if __name__ == '__main__':
    unittest.main()
