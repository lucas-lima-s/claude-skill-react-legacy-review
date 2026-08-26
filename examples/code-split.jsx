import React, { Suspense } from "react"

function RouteSkeleton() {
  return <div className="route-skeleton">Loading...</div>
}

const ApprovalWorkflow = React.lazy(() => import("./ApprovalWorkflow"))

function ApprovalRoute(props) {
  return (
    <Suspense fallback={<RouteSkeleton />}>
      <ApprovalWorkflow {...props} />
    </Suspense>
  )
}

function AdvancedExportRoute({ flags, ...props }) {
  if (!flags.advancedExport) return null
  const AdvancedExport = React.lazy(() => import("./AdvancedExport"))
  return (
    <Suspense fallback={<RouteSkeleton />}>
      <AdvancedExport {...props} />
    </Suspense>
  )
}

const routes = [
  { path: "/approvals", component: ApprovalRoute },
  { path: "/export/advanced", component: AdvancedExportRoute },
]

export default routes
