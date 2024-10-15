name: Autoloader

on:
  schedule:
    - cron: '0 9-22 * * MON-FRI'

jobs:
  worker:
    runs-on: ubuntu-latest
    env:
      output_dir: ./
      file_name: tmp.md

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Dependency
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run
        run: |
          python -m script.worker --output_dir $output_dir --file_name $file_name

      - name: Commit
        id: commit
        run: |
          if [ -n "$(git status --porcelain README.md)" ]; then
            git config --local user.email "github-actions[bot]@users.noreply.github.com"
            git config --local user.name "github-actions[bot]"
            git add README.md
            git commit -m "docs: update blog"
            echo "hasChange=true" >> $GITHUB_OUTPUT
          else
            echo "No changes detected"
          fi

      - name: Push
        uses: ad-m/github-push-action@master
        if: ${{ steps.commit.outputs.hasChange == 'true' }}
        with:
          github_token: ${{ secrets.TOKEN }}
          branch: ${{ github.ref }}

          
          