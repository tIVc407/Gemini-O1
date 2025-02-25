API Reference
============

REST API Endpoints
-----------------

The Gemini-O1 web interface provides a RESTful API for interacting with the system.

Instance Management
^^^^^^^^^^^^^^^^^^

.. http:get:: /api/instances

   List all active instances with details.

   **Example response**:

   .. sourcecode:: json

      {
        "mother_node": {
          "role": "scrum_master",
          "id": "mother"
        },
        "instances": [
          {
            "name": "instance_0",
            "role": "research_assistant",
            "id": "inst_1"
          },
          {
            "name": "instance_1",
            "role": "code_reviewer",
            "id": "inst_2"
          }
        ]
      }

.. http:get:: /api/instance/(instance_id)

   Get detailed information about a specific instance.

   :param instance_id: The ID of the instance to retrieve

   **Example response**:

   .. sourcecode:: json

      {
        "name": "instance_0",
        "role": "research_assistant",
        "instance_id": "inst_1",
        "model_name": "gemini-1.5-flash",
        "created_at": 1709118521.45,
        "connection_count": 1,
        "output_count": 3,
        "task_completed": true
      }

Message Handling
^^^^^^^^^^^^^^^

.. http:post:: /api/send_message

   Send a message to the network for processing.

   **Example request**:

   .. sourcecode:: json

      {
        "message": "Write a short story about robots"
      }

   **Example response**:

   .. sourcecode:: json

      {
        "response": "In the gleaming city of New Aurora, robots of all shapes and sizes..."
      }

Network Management
^^^^^^^^^^^^^^^^^

.. http:get:: /api/network/stats

   Get comprehensive network statistics.

   **Example response**:

   .. sourcecode:: json

      {
        "instance_count": 3,
        "total_messages": 42,
        "mother_node_status": "active",
        "uptime": 1256.32
      }

.. http:post:: /api/clear

   Clear all instances and history.

   **Example response**:

   .. sourcecode:: json

      {
        "success": true
      }

Health Monitoring
^^^^^^^^^^^^^^^^

.. http:get:: /api/health

   Get basic health status of the system.

   **Example response**:

   .. sourcecode:: json

      {
        "status": "healthy",
        "timestamp": "2023-02-25T14:35:12.432",
        "uptime_seconds": 3600.5,
        "checks": [
          {
            "name": "api_connectivity",
            "status": "healthy", 
            "message": "API connectivity is good"
          },
          {
            "name": "system_resources",
            "status": "healthy",
            "message": "System resources are sufficient"
          }
        ]
      }

.. http:get:: /api/health/detailed

   Get detailed health information including metrics.

.. http:get:: /api/metrics

   Get performance metrics for API calls and system resources.

.. http:get:: /api/health/check/(check_name)

   Run a specific health check.

   :param check_name: The name of the health check to run