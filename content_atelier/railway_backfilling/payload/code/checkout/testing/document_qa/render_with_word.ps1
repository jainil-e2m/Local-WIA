param(
    [string]$DocumentPath,
    [string]$RenderDirectory
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$atelierRoot = Split-Path -Parent $taskRoot
if (-not $DocumentPath) {
    $DocumentPath = Join-Path $atelierRoot 'client_review\week1_content_angles_for_review.docx'
}
if (-not $RenderDirectory) {
    $RenderDirectory = Join-Path $PSScriptRoot 'render'
}
$pdfPath = Join-Path $renderDirectory 'word_review.pdf'
New-Item -ItemType Directory -Path $renderDirectory -Force | Out-Null
$taskWord = $null
$taskDocument = $null
try {
    # Create a dedicated instance; do not attach to or close the user's open documents.
    $taskWord = New-Object -ComObject Word.Application
    $taskWord.Visible = $false
    $taskWord.DisplayAlerts = 0
    $taskWord.AutomationSecurity = 3
    $taskDocument = $taskWord.Documents.Open($documentPath, $false, $true, $false)
    $taskDocument.Repaginate()
    $taskDocument.ExportAsFixedFormat($pdfPath, 17)
    [PSCustomObject]@{pdf=$pdfPath; pages=$taskDocument.ComputeStatistics(2)} | ConvertTo-Json
} finally {
    if ($null -ne $taskDocument) {
        $taskDocument.Close(0)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($taskDocument)
    }
    if ($null -ne $taskWord) {
        try {
            $taskWord.Quit(0)
        } catch {
            if ($_.Exception.Message -notmatch '0x800706BA|RPC server is unavailable') {
                throw
            }
            Write-Verbose 'The dedicated Word instance already terminated after closing its document.'
        }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($taskWord)
    }
}
