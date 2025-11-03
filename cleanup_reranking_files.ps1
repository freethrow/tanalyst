# PowerShell script to clean up reranking files

# List of files to remove
$filesToRemove = @(
    "c:\Users\DELL\Desktop\TA\articles\direct_reranking.py",
    "c:\Users\DELL\Desktop\TA\articles\simple_reranking.py",
    "c:\Users\DELL\Desktop\TA\articles\huggingface_reranking.py",
    "c:\Users\DELL\Desktop\TA\articles\reranking.py",
    "c:\Users\DELL\Desktop\TA\huggingface_token_setup.py",
    "c:\Users\DELL\Desktop\TA\simple_reranker_test.py",
    "c:\Users\DELL\Desktop\TA\install_lightweight_reranker.py",
    "c:\Users\DELL\Desktop\TA\install_reranker.py",
    "c:\Users\DELL\Desktop\TA\setup_reranker.py",
    "c:\Users\DELL\Desktop\TA\test_reranking.py",
    "c:\Users\DELL\Desktop\TA\test_huggingface_reranker.py",
    "c:\Users\DELL\Desktop\TA\test_public_reranker.py",
    "c:\Users\DELL\Desktop\TA\use_direct_reranker.py"
)

# Delete each file if it exists
foreach ($file in $filesToRemove) {
    if (Test-Path $file) {
        Write-Host "Removing $file"
        Remove-Item -Path $file -Force
    } else {
        Write-Host "File not found: $file"
    }
}

Write-Host "`nCleanup complete!"
