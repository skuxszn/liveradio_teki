import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import assetService from '@/services/asset.service'
import mappingService from '@/services/mapping.service'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'

export default function OnboardingChecklist() {
  const nav = useNavigate()
  const { data: assetStats } = useQuery({ queryKey: ['asset-stats'], queryFn: () => assetService.getStats() })
  const { data: mappingStats } = useQuery({ queryKey: ['mapping-stats'], queryFn: () => mappingService.getStats() })

  const needsAssets = (assetStats?.total_assets || 0) === 0
  const needsMappings = (mappingStats?.total_mappings || 0) === 0
  if (!needsAssets && !needsMappings) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Get set up</CardTitle>
        <CardDescription>Complete these steps to start streaming with visuals.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {needsAssets && (
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Upload your first video asset</div>
              <div className="text-sm text-gray-600">MP4 loop files will be used during streaming.</div>
            </div>
            <Button onClick={() => nav('/assets')}>Upload</Button>
          </div>
        )}
        {needsMappings && (
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Create your first track mapping</div>
              <div className="text-sm text-gray-600">Map a track (artist + title) to a video loop.</div>
            </div>
            <Button onClick={() => nav('/mappings')}>Create Mapping</Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}



