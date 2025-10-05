### Links manifest from db

```json
{
  "meta": {
    "manifestId": "uuid-string",
    "workspaceId": "uuid-string",
    "version": "v1",
    "updatedAt": "2025-08-30T20:30:00Z",
    "iconStyle": "default"
  },
  "actionButton": {
    "type": "link",
    "id": "new-workorder"
  },
  "items": [
    {
      "type": "section",
      "id": "general",
      "titleKey": "nav.general",
      "children": [
        {
          "type": "link",
          "id": "workshop.calendar"
        },
        {
          "type": "link",
          "id": "workshop.workorders"
        }
      ]
    },
    {
      "type": "section",
      "id": "crm",
      "titleKey": "nav.crm",
      "children": [
        {
          "type": "link",
          "id": "mechanical-workshop.customers"
        },
        {
          "type": "group",
          "id": "notifications_module.notifications",
          "children": [
            {
              "type": "link",
              "id": "notifications_module.list"
            }
          ]
        },
        {
          "type": "link",
          "id": "repair_tracking.main"
        }
      ]
    }
  ]
}
```

### Fusion (layering)

GLOBAL < WORKSPACE < MODULE(S) (por priority) < USER
