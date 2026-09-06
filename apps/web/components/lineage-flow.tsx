import { Icon } from "./icon";

type LineageNode = { key: string; name: string; nodeType: string; description: string };

const stageOrder = ["SOURCE", "DATASET", "PROCESS", "API", "DASHBOARD"];

function groupedNodes(nodes: LineageNode[]) {
  return stageOrder.map((stage) => ({
    stage,
    nodes: nodes.filter((node) => node.nodeType === stage),
  })).filter((group) => group.nodes.length > 0);
}

export function LineageFlow({ nodes }: { nodes: LineageNode[] }) {
  const groups = groupedNodes(nodes);
  return (
    <ol className="lineage-track" aria-label="Dependency flow from source to dashboard">
      {groups.map((group, index) => (
        <li className="lineage-stage" key={group.stage}>
          <div className="lineage-stage-label"><span>{group.stage}</span><small>{index + 1} of {groups.length}</small></div>
          <div className="lineage-stage-nodes">
            {group.nodes.map((node) => (
              <article className={`lineage-node lineage-node-${node.nodeType.toLowerCase()}`} key={node.key}>
                <strong>{node.name}</strong>
                <span>{node.description}</span>
                <code>{node.key}</code>
              </article>
            ))}
          </div>
          {index < groups.length - 1 && <span className="lineage-connector" aria-hidden="true"><Icon name="arrow-right" size={18} /><span>feeds</span></span>}
        </li>
      ))}
    </ol>
  );
}
